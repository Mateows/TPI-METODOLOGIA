# TPI Metodología — SaaS Odontológico

SaaS multi-tenant para clínicas odontológicas: gestión de pacientes, agenda de turnos por profesional y box, caja y facturación electrónica AFIP/ARCA, con portal público de reservas y panel administrativo.

## Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy + Alembic, Pydantic Settings, pytest.
- **Frontend** (futuro, C-09/C-10): React 18+ con TypeScript y Tailwind CSS.
- **Base de datos**: PostgreSQL 16.
- **Infra**: Docker Compose. El servicio `db` expone el **puerto 5433** en el host porque el 5432 suele estar ocupado.

## Estructura del repo

- `backend/` — API FastAPI (routers, servicios, modelos, migraciones, tests).
- `knowledge-base/` — documentación canónica del proyecto (10 archivos).
- `docs/discovery/` — informe de discovery (`informe-discovery.pdf`).
- `openspec/` — specs y changes del ciclo de vida OpenSpec/OPSX.
- `CHANGES.md` — índice canónico de los 10 changes (C-01..C-10) en 4 fases.

## Cómo levantar

Prerrequisito honesto: **Docker Desktop** (para PostgreSQL) + **Python 3.12**.

```bash
docker compose up -d db
cd backend
set DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev
set TEST_DATABASE_URL=postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_test
alembic upgrade head
pytest  # 23 tests
```

## Documentación

- [knowledge-base/](knowledge-base/) — visión, reglas de negocio, modelo de datos y arquitectura.
- [CHANGES.md](CHANGES.md) — roadmap de changes y camino crítico.
- [docs/discovery/informe-discovery.pdf](docs/discovery/informe-discovery.pdf) — informe de discovery.

## Notas

- **Ley 25.326**: no usar datos reales de pacientes; sin datos sensibles en logs ni en el repo.
- **Alcance**: `C-01` sellado y archivado; `C-02`..`C-10` fuera de alcance por consigna.
