# Proposal

## Why

The repo is greenfield: foundation docs only, no runnable code. Every change C-02→C-10 depends on a working backend skeleton, database, and test harness. C-01 (GATE 0) unblocks the whole sequence.

## What Changes

- `backend/` layout per KB 08 §2: `app/api/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/main.py`, plus `alembic/` and `tests/`.
- `docker-compose.yml`: PostgreSQL service for local dev + test database path.
- SQLAlchemy 2.0 (async via `asyncpg`) base + session wiring; Alembic initialized with async-compatible `env.py`.
- Pydantic Settings (`app/core/config.py`) loading `.env` (`DATABASE_URL`, `SECRET_KEY`, placeholders for `WHATSAPP_API_TOKEN`, `AFIP_CERT_PATH`, `AFIP_CUIT`); commit `.env.example`, never `.env` (already gitignored).
- `GET /health` endpoint (liveness + DB check) as bootstrap proof.
- pytest + async fixtures: test client, DB session override against a separate test database, Alembic-upgrade-at-session-start helper.

## Capabilities

### New Capabilities

- `backend-foundation`: verifiable bootstrap behaviors — app boots from env config, exposes health, connects to Compose PostgreSQL, runs migrations, and the pytest harness passes against an isolated test DB.

### Modified Capabilities

(none — greenfield, no existing specs)

## Impact

- New files under `backend/`, `docker-compose.yml`, `.env.example`. No API surface beyond `/health`.
- Dependencies added: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `pytest`, `pytest-asyncio`, `httpx`.
- Unblocks C-02 (models/auth build on this skeleton and session wiring).

## Out of Scope

- `Clinic`/`User`/any domain models, JWT/RBAC (C-02); any business endpoints; frontend; WhatsApp/Mercado Pago/AFIP integrations; production deploy (Railway/Render staging config comes later); multi-sucursal/`branch_id` (deferred to V2, D-3).
