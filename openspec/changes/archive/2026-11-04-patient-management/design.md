# Design

## Context

Ver `proposal.md` — Why. Estado actual del proyecto tras `C-02`:

- `app/core/database.py` provee `Base` (`DeclarativeBase` con `NAMING_CONVENTION`), `engine`, `SessionLocal`, `get_db` y `utcnow()` (`datetime.now(UTC)`).
- `app/models/mixins.py` define `UuidPrimaryKeyMixin` (`id` UUID v4) y `TimestampMixin` (`created_at`, `updated_at` con `DateTime(timezone=True)`).
- `app/repositories/base.py` provee `TenantScopedRepository[ModelT]` (D13), que exige `hasattr(model, "clinic_id")` y acota toda lectura a `model.clinic_id == principal.clinic_id`.
- `app/api/deps.py` expone `get_current_principal` y `require_roles(*roles)` (`admin`, `receptionist`, `dentist`), garantizando que tanto el usuario como su clínica estén activos antes de ejecutar cualquier handler.
- `app/core/errors.py` centraliza `DomainError` y sus subclases con respuesta uniforme `{"detail": str, "code": str}` sin exponer trazas de SQLAlchemy.
- `tests/test_architecture.py` aplica una guarda AST estática sobre `app/services/` y `app/cli/` que prohíbe importar constructores SQL (`select`, `func`, `insert`, `update`, `delete`) o invocar métodos de persistencia sobre la sesión (`execute`, `scalar`, `scalars`, `get`, `add`, `add_all`, `delete`, `begin_nested`).
- `alembic/versions/0002_core_models_tenants.py` es el head actual de migraciones.

## Goals / Non-Goals

**Goals:**

- Persistir `Patient` cumpliendo estrictamente el aislamiento multi-tenant (`clinic_id`), la convención de tipos portables PostgreSQL/SQLite y la unicidad de DNI por clínica.
- Encapsular toda consulta y persistencia en `PatientRepository` (`app/repositories/patients.py`) manteniendo `test_architecture.py` en verde.
- Proveer una API REST clara, tipada con Pydantic V2 (`extra="forbid"`) y protegida por RBAC para que el personal de la clínica gestione pacientes y su anamnesis médica resumida (`medical_history_summary`).
- Garantizar que los intentos de acceso cruzado entre clínicas respondan `404 Not Found` indistinguible de un ID inexistente y que jamás se registren datos sensibles de salud o identificadores de pacientes en logs (Ley 25.326).

**Non-Goals:**

- Entidades clínicas detalladas (`Odontogram`, `MedicalRecord` en `C-05`) o financieras (`Budget`, `AccountEntry`, `Invoice` en `C-05`/`C-07`/`C-08`).
- Cifrado de columnas con KMS externo (el aislamiento lógico estricto por `clinic_id` y el almacenamiento controlado sin exposición en logs cubren el alcance del MVP; el cifrado de disco/volumen corresponde a la infraestructura).
- Borrado físico (`DELETE`) de pacientes, para no romper la integridad referencial futura con turnos, historias clínicas y comprobantes.
- UI de gestión de pacientes (`C-10`).

## UI Mockups

Decision: no (no UI)

## Decisions

### D1 — Modelo `Patient` con `clinic_id` explícito y unicidad `(clinic_id, dni)`

`Patient` (`app/models/patient.py`) hereda de `UuidPrimaryKeyMixin`, `TimestampMixin` y `Base`. Siguiendo el patrón de `User` y `RefreshToken` en `C-02`, declara explícitamente:
- `clinic_id: Mapped[uuid.UUID]` (`ForeignKey("clinics.id", ondelete="CASCADE")`, `nullable=False`, `index=True`).
- `first_name: Mapped[str]` (`String(120)`, `nullable=False`) y `last_name: Mapped[str]` (`String(120)`, `nullable=False`).
- `dni: Mapped[str]` (`String(32)`, `nullable=False`), normalizado en la capa de entrada (sin espacios ni puntos separadores).
- `email: Mapped[str | None]` (`String(255)`, `nullable=True`, normalizado a minúsculas si se provee), `phone: Mapped[str | None]` (`String(50)`, `nullable=True`), `birth_date: Mapped[date | None]` (`Date`, `nullable=True`).
- `medical_history_summary: Mapped[dict[str, Any] | None]` (`JSON`, `nullable=True`), portable entre PostgreSQL y SQLite.
- `is_active: Mapped[bool]` (`Boolean`, `default=True`, `nullable=False`).
- `UniqueConstraint("clinic_id", "dni")` en `__table_args__` (nombrado automáticamente por `NAMING_CONVENTION` como `uq_patients_clinic_id`) e índice de búsqueda sobre `(clinic_id, last_name, first_name)`.

*Alternativa considerada:* `dni` único global en toda la base. *Rechazada:* dos clínicas distintas pueden atender a la misma persona física; una restricción global impediría registrarla en la segunda clínica y revelaría que ya existe en otro tenant, violando `tenant-isolation` y la Ley 25.326.

### D2 — `medical_history_summary` como documento JSON validado (`dict[str, Any]`)

La KB (`04_modelo_de_datos.md` §1) define `medical_history_summary` como `JSON` en `Patient` para almacenar la anamnesis resumida (alergias, medicación habitual, patologías de base, alertas médicas) antes de las evoluciones clínicas (`MedicalRecord`, `C-05`). En los schemas Pydantic (`PatientCreate`, `PatientUpdate`, `PatientResponse`), se tipa como `dict[str, Any] | None = None`. Esto rechaza con `422` valores primitivos o listas en la raíz, permite evolucionar las claves de anamnesis en `C-05`/`C-10` sin migraciones adicionales y mantiene compatibilidad total entre SQLite y PostgreSQL.

*Alternativa considerada:* crear una tabla separada `PatientAnamnesis`. *Rechazada:* contradice el modelo canónico de la KB (`04_modelo_de_datos.md`) y agrega joins innecesarios para datos que siempre se leen junto con la ficha del paciente.

### D3 — `PatientRepository` sobre `TenantScopedRepository` y manejo de colisiones con savepoint

`PatientRepository` (`app/repositories/patients.py`) extiende `TenantScopedRepository[Patient]` (que ya provee `get(record_id)` y `scoped(*criteria)` filtrados por `principal.clinic_id`) y añade:
- `get_by_dni(dni: str) -> Patient | None`: consulta acotada a `self.principal.clinic_id`.
- `dni_exists(dni: str, exclude_id: uuid.UUID | None = None) -> bool`: verifica disponibilidad del DNI dentro de la clínica activa.
- `search(q: str | None = None, *, include_inactive: bool = False, limit: int = 50, offset: int = 0) -> Sequence[Patient]`: filtra por `clinic_id`, por `is_active == True` cuando `include_inactive=False`, y si `q` no está vacío aplica coincidencia case-insensitive (`ilike`) sobre `dni`, `first_name` o `last_name`, ordenando por `last_name ASC, first_name ASC, id ASC`.
- `add(patient: Patient) -> Patient` y `save(patient: Patient) -> Patient`: ejecutan `flush()` dentro de un savepoint (`async with self.db.begin_nested():`) para capturar `IntegrityError` ante condiciones de carrera en `(clinic_id, dni)` sin corromper la transacción de la sesión.

En cumplimiento de la Regla 4 y D13 (`test_architecture.py`), `app/services/patients.py` no importa nada de `sqlalchemy` ni llama métodos de persistencia sobre `AsyncSession`; delega 100% en `PatientRepository` y el router ejecuta `await db.commit()`.

### D4 — Permisos RBAC para el padrón de pacientes

Los endpoints de `/api/v1/patients` requieren `require_roles("admin", "receptionist", "dentist")`:
- `receptionist` y `admin` necesitan dar de alta, buscar y actualizar datos filiatorios para recepción y turnos (`C-04`) y facturación (`C-07`/`C-08`).
- `dentist` necesita consultar y actualizar la ficha del paciente y su `medical_history_summary` durante la atención clínica (`03_actores_y_roles.md` §2).

*Alternativa considerada:* restringir `medical_history_summary` en un endpoint separado solo para `dentist`. *Rechazada:* en consultorios pequeños/medianos la carga inicial de la ficha de ingreso (incluyendo cuestionario de anamnesis) suele asistirla recepción o el propio profesional indistintamente; la segregación de historia clínica estricta (`MedicalRecord` y `Odontogram`) se aplica en los módulos de `C-05` conforme a la matriz RBAC.

### D5 — Desactivación lógica (`is_active`) en lugar de `DELETE`

No se expone `DELETE /api/v1/patients/{id}`. La baja de un paciente se realiza mediante `PATCH /api/v1/patients/{id}` con `{"is_active": false}`. Por defecto `GET /api/v1/patients` devuelve únicamente pacientes activos (`is_active=True`), pudiendo incluir inactivos con `?include_inactive=true`. Esto preserva la integridad referencial futura con turnos (`Appointment`), evoluciones (`MedicalRecord`), presupuestos (`Budget`) y comprobantes (`Invoice`), además de cumplir con los deberes legales de conservación de documentación clínica.

### D6 — Errores semánticos y privacidad en logs (Ley 25.326)

Se agregan en `app/core/errors.py`:
- `DuplicateDni(DomainError)` → HTTP `409`, `code = "duplicate_dni"`, `default_detail = "a patient with that DNI already exists in this clinic"`.
- `PatientNotFound(DomainError)` → HTTP `404`, `code = "not_found"`, `default_detail = "resource not found"` (mismo `status_code`, `code` y `detail` que `TenantViolation`, garantizando que un ID de otra clínica y un ID inexistente produzcan respuestas idénticas).

Ningún servicio, repositorio ni handler loguea `dni`, nombres, contacto ni `medical_history_summary`.

## Risks / Trade-offs

- **Condición de carrera en alta/edición con mismo DNI en la misma clínica** → Mitigación: además de la verificación previa con `repo.dni_exists(...)`, la restricción `UniqueConstraint("clinic_id", "dni")` en base de datos y el savepoint (`begin_nested()`) en `PatientRepository` convierten cualquier `IntegrityError` en `DuplicateDni` (409) sin exponer trazas SQL.
- **Búsqueda con `ILIKE` sobre tablas grandes** → Mitigación: las consultas siempre filtran primero por el índice `ix_patients_clinic_id` y por `(clinic_id, last_name, first_name)` con límite paginado (`limit` máximo de 100, default 50).
- **Diferencias de comportamiento de `Date` y `JSON` entre SQLite y PostgreSQL** → Mitigación: usar los tipos estándar `sqlalchemy.Date` y `sqlalchemy.JSON` y correr toda la suite de tests en ambos motores antes de cerrar el change.
- **Tests preexistentes de esquema/migraciones (`test_migrations.py`, `test_database.py`)** → Mitigación: actualizar las expectativas de versión `head` (`0003_patient_management`) y del conjunto de tablas registradas en `Base.metadata` como parte de las tareas de migración.

## Migration Plan

1. Crear `backend/alembic/versions/0003_patient_management.py` con `revision = "0003_patient_management"` y `down_revision = "0002_core_models_tenants"`, definiendo la tabla `patients`, su `ForeignKey("clinics.id", ondelete="CASCADE")`, la restricción única `uq_patients_clinic_id` sobre `(clinic_id, dni)` y los índices `ix_patients_clinic_id` e `ix_patients_clinic_id_last_name_first_name`.
2. Registrar `Patient` en `backend/app/models/__init__.py` para que `Base.metadata` y `alembic check` lo reconozcan.
3. Verificar `alembic upgrade head`, idempotencia de segunda corrida y ciclo `alembic downgrade 0002_core_models_tenants` → `upgrade head`.
4. Rollback: `alembic downgrade 0002_core_models_tenants` elimina la tabla `patients` y sus índices limpiamente.

## Open Questions

- Ninguna pregunta bloqueante. La estructura interna de claves sugeridas dentro de `medical_history_summary` (p. ej., `allergies`, `medications`, `conditions`, `notes`) podrá enriquecerse en `C-05` (`odontogram-clinical-records`) y `C-10` sin romper el contrato `dict[str, Any]` definido en este change.
