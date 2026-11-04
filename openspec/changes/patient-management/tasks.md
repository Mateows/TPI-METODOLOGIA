# Tasks

## 1. Modelo `Patient` y Migración Alembic

- [x] 1.1 Implementar el modelo `Patient` en `backend/app/models/patient.py` (`UuidPrimaryKeyMixin`, `TimestampMixin`, `clinic_id` FK indexado con `ondelete="CASCADE"`, `first_name`, `last_name`, `dni`, `email`, `phone`, `birth_date`, `medical_history_summary` JSON, `is_active`, `UniqueConstraint("clinic_id", "dni")` e índice compuesto `(clinic_id, last_name, first_name)`) y exportarlo en `backend/app/models/__init__.py`; verificar con tests de esquema en `backend/tests/test_patients.py` (y actualizando `backend/tests/test_database.py` si valida el listado exacto de tablas de `Base.metadata`) que existen todas las columnas, constraints e índices.
- [x] 1.2 Crear la migración `backend/alembic/versions/0003_patient_management.py` (`revision = "0003_patient_management"`, `down_revision = "0002_core_models_tenants"`) y actualizar `backend/tests/test_migrations.py` para esperar `0003_patient_management` como head; verificar ejecutando `pytest tests/test_migrations.py` incluyendo el ciclo `upgrade head`, `downgrade 0002_core_models_tenants` y `upgrade head` más `alembic check` sin diferencias pendientes.

## 2. Errores de Dominio, Schemas Pydantic y Repositorio Multi-Tenant

- [x] 2.1 Agregar `DuplicateDni` (HTTP 409, `code="duplicate_dni"`) y `PatientNotFound` (HTTP 404, `code="not_found"`, mismo contrato que `TenantViolation`) en `backend/app/core/errors.py`, e implementar `backend/app/schemas/patients.py` (`PatientCreate`, `PatientUpdate`, `PatientResponse` con `extra="forbid"`, normalización de `dni` y `email`, validación de `birth_date` no futura y `medical_history_summary: dict[str, Any] | None`); verificar con tests unitarios en `backend/tests/test_patients.py` el rechazo (422) de `clinic_id` inyectado, `dni` vacío, `birth_date` futura y `medical_history_summary` no-objeto.
- [x] 2.2 Implementar `PatientRepository` en `backend/app/repositories/patients.py` heredando de `TenantScopedRepository[Patient]` (`get_by_dni`, `dni_exists`, `search` con filtro `q`, `include_inactive`, `limit` y `offset`, `add` y `save` con savepoint) y exportarlo en `backend/app/repositories/__init__.py`; verificar con tests unitarios en `backend/tests/test_repositories.py` que las consultas por ID, DNI y búsqueda nunca retornan registros de otra clínica y que el duplicado de `(clinic_id, dni)` en la misma clínica se detecta mientras el mismo DNI en otra clínica es permitido.

## 3. Servicio de Dominio y Endpoints REST (`/api/v1/patients`)

- [x] 3.1 Implementar `backend/app/services/patients.py` (`create_patient`, `list_patients`, `get_patient`, `update_patient`) orquestando validaciones de unicidad de DNI por clínica y delegando toda persistencia a `PatientRepository`; verificar que `pytest tests/test_architecture.py` pasa en verde garantizando ausencia de imports SQLAlchemy o llamadas directas sobre `AsyncSession` en `app/services/`.
- [x] 3.2 Implementar el router `backend/app/api/patients.py` (`POST /api/v1/patients`, `GET /api/v1/patients`, `GET /api/v1/patients/{id}`, `PATCH /api/v1/patients/{id}`) con `require_roles("admin", "receptionist", "dentist")` y registrarlo en `backend/app/main.py`; verificar con tests de integración en `backend/tests/test_patients.py` los escenarios de alta exitosa (201), DNI duplicado en la misma clínica (409 `duplicate_dni`), mismo DNI en distinta clínica (201), búsqueda por `q` (`dni`, `first_name`, `last_name`), actualización parcial de datos y `medical_history_summary` (200), desactivación lógica (`is_active=false`) y acceso sin token (401) o con clínica inactiva (403).
- [x] 3.3 Verificar con tests de aislamiento multi-tenant y privacidad en `backend/tests/test_patients.py` que `GET /api/v1/patients/{id}` y `PATCH /api/v1/patients/{id}` sobre un paciente de otra clínica responden `404 Not Found` (`code="not_found"`) idéntico a un UUID inexistente sin mutar datos, y que ninguna operación ni respuesta de error emite trazas SQL ni PII/`medical_history_summary` en logs (Ley 25.326).
- [x] 3.4 Documentar los endpoints, parámetros de búsqueda, estructura de `medical_history_summary` y códigos de error en `backend/docs/api-patients.md`; verificar que los ejemplos documentados coinciden con los schemas y contratos probados.

## 4. Verificación Integral y Cierre Pre-Archivo

- [x] 4.1 Ejecutar la suite completa de tests en SQLite y en PostgreSQL de Docker Compose (`TEST_DATABASE_URL`) y verificar que todos los tests pasan en verde sin escribir en la base de desarrollo `tpi_dev`.
- [x] 4.2 Ejecutar `openspec validate patient-management --strict` y actualizar el estado de `C-03` en `CHANGES.md` desbloqueando la dependencia hacia `C-05`.

## Workflow follow-up

- Aplicar Strict TDD Mode en cada tarea: escribir primero el test que falla (RED), implementar el código mínimo para pasar (GREEN), triangular casos borde (TRIANGULATE) y refactorizar manteniendo la suite en verde (REFACTOR).
- Archivar el change con `/openspec-archive-change patient-management` una vez completadas y verificadas todas las tareas, comprobando que `openspec/specs/patient-management/spec.md` quede sincronizado.
