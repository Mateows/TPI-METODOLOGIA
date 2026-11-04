# Proposal

## Why

Con `C-02` completado, el backend dispone de clínicas, usuarios, JWT y aislamiento multi-tenant por `clinic_id`, pero aún carece de la entidad `Patient` y de su API de administración. Sin el padrón de pacientes por clínica no se pueden vincular turnos (`C-04`), registrar odontogramas y evoluciones clínicas (`C-05`, Épica 2 / F-05), ni emitir cobros y comprobantes (`C-07`/`C-08`), ni garantizar la protección de datos sensibles exigida por RN-02 (Ley 25.326).

## What Changes

- Modelo SQLAlchemy `Patient` (`id` UUID, `clinic_id` FK indexado, `first_name`, `last_name`, `dni`, `email`, `phone`, `birth_date`, `medical_history_summary` JSON, `is_active`, timestamps UTC) con restricción de unicidad `(clinic_id, dni)`.
- Repositorio `PatientRepository` en `app/repositories/patients.py` heredando de `TenantScopedRepository[Patient]`, encapsulando toda consulta SQLAlchemy (búsqueda, paginación, lectura por ID y verificación de DNI por clínica) conforme a la Regla 4 y D13.
- Endpoints REST en `/api/v1/patients` (`POST /api/v1/patients`, `GET /api/v1/patients`, `GET /api/v1/patients/{id}`, `PATCH /api/v1/patients/{id}`) protegidos por JWT y guardas RBAC (`admin`, `receptionist`, `dentist`), siempre acotados al `clinic_id` del `Principal`.
- Manejo de errores semánticos (`DuplicateDni` → 409, `PatientNotFound` / intento cruzado entre clínicas → 404 indistinguible, payload inválido o inyección de `clinic_id` → 422) sin exponer trazas SQL ni registrar datos sensibles de pacientes en logs (Ley 25.326).
- Migración Alembic `0003_patient_management` y suite de tests unitarios, de repositorio y de integración multi-tenant con `pytest`.

**Fuera de alcance:** odontograma interactivo ISO 3950 y evoluciones clínicas `MedicalRecord` (`C-05`); presupuestos `Budget` y movimientos de cuenta corriente `AccountEntry` (`C-05`/`C-07`); agendamiento de turnos (`C-04`) y portal público de reservas (`C-09`); cifrado KMS externo; eliminación física (`DELETE`) de pacientes con historial clínico; vistas de interfaz en React (`C-10`).

## Capabilities

### New Capabilities

- `patient-management`: alta, consulta, búsqueda/listado, actualización parcial y desactivación lógica de pacientes con resumen de anamnesis médica (`medical_history_summary`), bajo aislamiento estricto por `clinic_id` y control de acceso por rol.

### Modified Capabilities

- Ninguna. `tenant-isolation` e `identity-access` se consumen sin modificar sus requisitos.

## Impact

- Backend: `app/models/patient.py` (y registro en `app/models/__init__.py`), `app/repositories/patients.py`, `app/services/patients.py`, `app/schemas/patients.py`, `app/api/patients.py`, `app/core/errors.py`, `app/main.py` y `alembic/versions/0003_patient_management.py`.
- Pruebas y documentación: `backend/tests/test_patients.py`, actualización de `test_migrations.py` / `test_database.py` si verifican el head o tablas exactas, y `backend/docs/api-patients.md`.
- Habilita: `C-05` (`odontogram-clinical-records`) y provee el modelo `Patient` requerido por `C-04`, `C-07` y `C-08`.
- Governance: MEDIO — reglas de negocio de dominio y repositorios multi-tenant con verificación por tests.
