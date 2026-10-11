# Tasks

## 1. Scaffolding y dependencias

- [x] 1.1 Create `backend/` layout (`app/api/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/main.py`, `tests/`) per KB 08 §2 and verify expected paths exist
- [x] 1.2 Pin `backend/requirements.txt` (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, pytest, pytest-asyncio, httpx) and verify `pip install -r requirements.txt` succeeds in a clean venv

## 2. Configuración por entorno

- [x] 2.1 Implement `app/core/config.py` (Pydantic Settings: `DATABASE_URL`, `TEST_DATABASE_URL`, `SECRET_KEY`, optional `WHATSAPP_API_TOKEN`/`AFIP_CERT_PATH`/`AFIP_CUIT`) with fail-fast on missing required vars and verify import without `.env` raises naming the missing variable
- [x] 2.2 Add committed `.env.example` (placeholder values, no secrets) and verify `diff` of required keys between `config.py` and `.env.example` shows no missing key

## 3. Base de datos y migraciones

- [x] 3.1 Implement `app/core/database.py` (async engine, session factory, Declarative `Base`, `get_db` dependency) and verify a round-trip test opens/closes a session against the Compose DB
- [x] 3.2 Create `docker-compose.yml` (PostgreSQL 16, persisted volume, healthcheck; dev + test database URLs documented) and verify `docker compose up -d db` reaches healthy status
- [x] 3.3 Initialize Alembic with async-compatible `env.py` wired to `Base.metadata` and verify `alembic upgrade head` then `downgrade -1`/`upgrade head` on an empty DB leaves zero pending revisions

## 4. API bootstrap y health

- [x] 4.1 Implement `app/main.py` (app factory, layered router include point) plus `GET /health` (app + DB status, no logging of request bodies) and verify `200` with healthy payload when DB is reachable
- [x] 4.2 Cover DB-unreachable path and verify `/health` reports unhealthy (non-`200` or explicit unhealthy payload) when the database is stopped

## 5. Harness de tests e integración final

- [x] 5.1 Add `tests/conftest.py` fixtures (async client, session dependency override to isolated test DB, per-test rollback, session-scoped Alembic upgrade) and verify a marker test writes only to the test database
- [x] 5.2 Run full acceptance (`docker compose up -d db`, `alembic upgrade head`, `pytest`) and verify green suite plus documented commands in this task reproduce it as written

> Cierre aceptado por el usuario (Opción 2, 2026-10-09): suite 23/23 verde + ciclo Alembic
> upgrade/downgrade/upgrade verificado + venv limpio OK como evidencia suficiente para C-01.
> El paso contra Postgres real vía `docker compose up -d db` (sin Docker CLI en este entorno)
> queda como verificación del operador con los comandos documentados en `docker-compose.yml`.
>
> Apéndice operador (2026-10-11, Docker Desktop daemon v29.8.2): `docker compose up -d db`
> → `pg_isready` OK en tpi_dev; `alembic upgrade head` → `Running upgrade -> 0001_init`
> (EXIT 0) contra `postgresql+asyncpg://tpi:tpi@localhost:5433/tpi_dev`;
> `pytest -q` con ambas URLs en 5433 → **23 passed**. Opción 2 cerrada también contra
> Postgres 16 real; servicio `db` dejado levantado (`docker compose stop db` para bajarlo).
