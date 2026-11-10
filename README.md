# TPI Metodología — SaaS Odontológico

SaaS multi-tenant para clínicas odontológicas: gestión de pacientes, agenda de turnos por profesional y box, caja y facturación electrónica AFIP/ARCA, con portal público de reservas y panel administrativo.

## Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy + Alembic, Pydantic Settings, PyJWT + bcrypt, pytest.
- **Frontend** (futuro, C-09/C-10): React 18+ con TypeScript y Tailwind CSS.
- **Base de datos**: PostgreSQL 16 (con soporte SQLite en el harness de tests sin Docker).
- **Infra**: Docker Compose. El servicio `db` expone el **puerto 5433** en el host porque el 5432 suele estar ocupado.

## Estructura del repo

- `backend/` — API FastAPI en capas (`api/`, `services/`, `repositories/`, `models/`, `schemas/`, `cli/`), migraciones Alembic, documentación técnica (`backend/docs/`) y suite de tests (`tests/`).
- `knowledge-base/` — documentación canónica del proyecto (10 archivos + índice en `README.md`).
- `openspec/` — specs canónicas (`backend-foundation`, `identity-access`, `tenant-isolation`,
  `patient-management`, `appointment-agenda`) y changes del ciclo de vida OpenSpec/OPSX.
- `docs/` — informes y documentos del TP: discovery, skill propia y MCP, decisiones de
  fundación (`decisiones-fundacion-D1-D6.md`), mapeo de escenarios, justificación de skills
  y la reflexión del trabajo.
- `scripts/` — preparación y reproducción del demo (ver abajo).
- `CHANGES.md` — índice canónico de los 10 changes (`C-01`..`C-10`) en 4 fases.
- `ENTREGA.md` — índice de la entrega del TP (skill propia + servidor MCP).

## Cómo levantar

Prerrequisito honesto: **Docker Desktop** (para PostgreSQL) + **Python 3.12**.

```bash
docker compose up -d db
cd backend
set DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev
set TEST_DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test
set SECRET_KEY=dev-only-change-me
alembic upgrade head
pytest  # 259 tests (también corre sobre SQLite por defecto si no se exportan las URLs)
```

Para provisionar la primera clínica y su usuario `admin` de forma idempotente (ver [`backend/docs/api-auth.md`](backend/docs/api-auth.md)):

```bash
set BOOTSTRAP_ADMIN_PASSWORD=<elegí-una-contraseña-local>
python -m app.cli.bootstrap_clinic --name "Clinica Demo Bootstrap" --tax-id "30-12345678-9" --email "admin@demo-bootstrap.com" --full-name "Ada Administradora"
```

La contraseña se pasa **solo por variable de entorno** y no se versiona. Lo mismo vale
para los scripts de demo: leen las credenciales de variables de entorno
(`TPI_DEMO_PASSWORD_A`, `TPI_DEMO_PASSWORD_B`, `TPI_DEMO_PASSWORD_RECEPCION`), que se
cargan desde `scripts/demo-env.ps1` (ignorado por git). Copiá la plantilla y completá
con los valores de tu base local:

```powershell
Copy-Item scripts/demo-env.example.ps1 scripts/demo-env.ps1
```

Si la base local ya existía con otras contraseñas, aplicalas con
`.\scripts\rotate-demo-passwords.ps1` (no imprime secretos y es idempotente).

## Scripts de demo

Desde la raíz del repo, en PowerShell:

| Script | Para qué |
|---|---|
| `.\scripts\chequear-video.ps1` | Chequeo previo: Docker, base, API, archivos y variables. |
| `.\scripts\preflight-demo.ps1` | Deja el entorno listo y reproducible: levanta PostgreSQL, migra, crea las clínicas A y B, limpia lo que el demo crea en vivo y corre la suite. |
| `.\scripts\demo-video.ps1` | Recorre el mismo flujo que se muestra en el video: health, login, alta de usuario, duplicado, RBAC, aislamiento multi-tenant, sesiones y agenda. No imprime tokens: solo rol y largo. |
| `.\scripts\rotate-demo-passwords.ps1` | Aplica las contraseñas de `scripts/demo-env.ps1` a la base local. |

## Documentación

- [knowledge-base/](knowledge-base/) — visión, reglas de negocio, modelo de datos y arquitectura.
- [CHANGES.md](CHANGES.md) — roadmap de changes y camino crítico.
- [ENTREGA.md](ENTREGA.md) — índice de la entrega: skill propia, MCP, evidencias y requisitos.
- [backend/docs/api-auth.md](backend/docs/api-auth.md) — contrato de autenticación (`/api/v1/auth/*`), administración de usuarios (`/api/v1/users/*`), matriz RBAC y bootstrap de clínica.
- [docs/discovery/informe-discovery.pdf](docs/discovery/informe-discovery.pdf) — informe de discovery.
- [docs/decisiones-fundacion-D1-D6.md](docs/decisiones-fundacion-D1-D6.md) — decisiones de arquitectura de la fundación.
- [docs/skills-mcp/mcp-github.md](docs/skills-mcp/mcp-github.md) — integración del MCP `github`
  (requisitos, variables de entorno, verificación y solución de problemas).
- [docs/skills-mcp/](docs/skills-mcp/) — ficha de investigación e informe de aplicación de
  la skill propia y el MCP.

## Estado actual y notas

- **Ley 25.326**: no usar datos reales de pacientes; prohibido registrar credenciales, tokens o datos sensibles en logs o en el repo.
- **Estado de changes (ver [CHANGES.md](CHANGES.md))**:
  - **Fase 1 completada**: `C-01` (`foundation-setup`) y `C-02` (`core-models-tenants`,
    30/30 tareas con capa `repositories/` D13) implementados, verificados y archivados en
    `openspec/changes/archive/`.
  - **Fase 2 completada**: `C-03` (`patient-management`, 10/10 tareas) y `C-04`
    (`appointment-agenda`, 12/12 tareas) implementados, verificados y archivados.
    `C-04` se revisó antes de implementar con la skill propia `revisor-de-agendas-de-citas`.
  - **Pendiente**: `C-05` (odontograma) y `C-06`..`C-10` (recordatorios, caja, AFIP,
    portal público y frontend), declarados como tales en `CHANGES.md`.
- **Suite**: 259 tests en verde, con rollback por test, sobre SQLite y PostgreSQL.
- **Endpoints implementados**: `/health`, `/api/v1/auth/*`, `/api/v1/users`, `/api/v1/patients`,
  `/api/v1/boxes` y `/api/v1/appointments`.

## Entrega

El TP se entrega como **video de demostración + repositorio**. El índice de la entrega
(skill propia, servidor MCP, evidencias y cómo verificarlos) está en
[ENTREGA.md](ENTREGA.md).
