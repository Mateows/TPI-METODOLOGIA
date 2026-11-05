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
- `docs/discovery/` — informe de discovery (`informe-discovery.pdf`).
- `docs/skills-mcp/` — ficha de investigación, informe de aplicación y guía del MCP `github`.
- `openspec/` — specs principales (`backend-foundation`, `identity-access`, `tenant-isolation`) y changes del ciclo de vida OpenSpec/OPSX.
- `CHANGES.md` — índice canónico de los 10 changes (`C-01`..`C-10`) en 4 fases.

## Cómo levantar

Prerrequisito honesto: **Docker Desktop** (para PostgreSQL) + **Python 3.12**.

```bash
docker compose up -d db
cd backend
set DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev
set TEST_DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test
set SECRET_KEY=dev-only-change-me
alembic upgrade head
pytest  # 162 tests (también corre sobre SQLite por defecto si no se exportan las URLs)
```

Para provisionar la primera clínica y su usuario `admin` de forma idempotente (ver [`backend/docs/api-auth.md`](backend/docs/api-auth.md)):

```bash
set BOOTSTRAP_ADMIN_PASSWORD=Dev-Bootstrap-123
python -m app.cli.bootstrap_clinic --name "Clinica Demo Bootstrap" --tax-id "30-12345678-9" --email "admin@demo-bootstrap.com" --full-name "Ada Administradora"
```

## Documentación

- [knowledge-base/](knowledge-base/) — visión, reglas de negocio, modelo de datos y arquitectura.
- [CHANGES.md](CHANGES.md) — roadmap de changes y camino crítico.
- [backend/docs/api-auth.md](backend/docs/api-auth.md) — contrato de autenticación (`/api/v1/auth/*`), administración de usuarios (`/api/v1/users/*`), matriz RBAC y bootstrap de clínica.
- [docs/discovery/informe-discovery.pdf](docs/discovery/informe-discovery.pdf) — informe de discovery.
- [docs/skills-mcp/mcp-github.md](docs/skills-mcp/mcp-github.md) — integración del MCP `github`
  (requisitos, variables de entorno, verificación y solución de problemas).
- [docs/skills-mcp/](docs/skills-mcp/) — ficha de investigación e informe de aplicación de
  la skill propia y el MCP.

## Estado actual y notas

- **Ley 25.326**: no usar datos reales de pacientes; prohibido registrar credenciales, tokens o datos sensibles en logs o en el repo.
- **Estado de changes (ver [CHANGES.md](CHANGES.md))**:
  - **Fase 1 completada**: `C-01` (`foundation-setup`) y `C-02` (`core-models-tenants`, 30/30 tareas con capa `repositories/` D13 y 162 tests en verde en SQLite y PostgreSQL) implementados, verificados y archivados en `openspec/changes/archive/`.
  - **Fase 2 en preparación**: `C-04` (`appointment-agenda`) con artefactos propuestos y revisados con la skill `revisor-de-agendas-de-citas` (pendiente de implementar); `C-03` (`patient-management`) y `C-05`..`C-10` pendientes.
