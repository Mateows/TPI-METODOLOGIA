# Proposal

## Why

C-01 entregó un backend que arranca, migra y se testea, pero sin identidad: no
existen `Clinic` ni `User`, no hay JWT y ningún request tiene un `clinic_id`
confiable. Sin esa base no se puede cumplir RN-02 (segregación estricta por
clínica, Ley 25.326) ni implementar `appointment-agenda`, que ya está propuesto
y depende explícitamente de esta capacidad. Este change es el segundo eslabón
del camino crítico (C-01 → **C-02** → C-04 → C-07 → C-08 → C-10).

## What Changes

- Modelos persistentes `Clinic` y `User` (UUID, `clinic_id`, roles
  `admin`/`receptionist`/`dentist`, `is_active`, hash de contraseña).
- Autenticación JWT: access token de vida corta + refresh token persistido con
  hash, rotación, revocación y detección de reuso.
- Endpoints `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`,
  `POST /api/v1/auth/logout` y `GET /api/v1/auth/me`.
- Alta y administración de usuarios intra-clínica (`/api/v1/users`), exclusiva
  del rol `admin` y siempre acotada al `clinic_id` del token.
- Contexto multi-tenant por request: dependencia de autenticación que resuelve
  usuario + clínica activa, y guardas RBAC reutilizables por los routers de
  C-03/C-04.
- Bootstrap idempotente (script/CLI) que provisiona la primera clínica y su
  administrador; no hay auto-registro público.
- Migración `0002` y suite de tests de aislamiento, autenticación y
  autorización.
- Errores semánticos (401/403/409/422) sin filtrar trazas SQL ni datos
  sensibles en logs.

**Fuera de alcance:** pacientes, turnos, caja y facturación (C-03+); registro
público de clínicas; recuperación de contraseña por email; MFA/SSO; cifrado en
reposo de contenido clínico (se aplica cuando existan esos datos); entidad
`AuditLog` (C-06); pantallas de login/frontend (C-10); multi-sucursal
(`branch_id` es V2, D-3).

## Capabilities

### New Capabilities

- `identity-access`: autenticación de usuarios con access/refresh tokens,
  sesión revocable, ciclo de vida de contraseñas y alta de usuarios por un
  administrador de la clínica.
- `tenant-isolation`: resolución del contexto de clínica por request y
  garantía de que toda lectura/escritura autenticada queda acotada a
  `clinic_id`, con verificación de rol.

### Modified Capabilities

- Ninguna. `backend-foundation` no cambia: C-02 se apoya en la configuración y
  el harness que C-01 ya especificó.

## Impact

- Backend: `models/` (Clinic, User, RefreshToken), `core/security.py`,
  `services/`, `schemas/`, `api/auth.py`, `api/users.py`,
  `alembic/versions/0002_core_models_tenants.py` y `tests/` (auth, RBAC y
  aislamiento).
- Dependencia nueva: `PyJWT` y `bcrypt` (design D1), fijadas en
  `requirements`.
- Habilita: `appointment-agenda` (C-04) y todo el resto del roadmap.
- Riesgo: governance CRÍTICO — auth se implementa con checkpoints de revisión
  antes de escribir el código de autorización.
