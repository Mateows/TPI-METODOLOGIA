# Design

## Context

Greenfield repo: docs only, no `backend/` code. See proposal.md Why. Constraints shaping the approach: KB 08 §2 layout (`api/`, `core/`, `models/`, `schemas/`, `services/`, `main.py`, `alembic/`, `tests/`); strict `clinic_id` tenant isolation and UTC persistence required by all later changes, so the session/base wiring must make those defaults hard to bypass; `.env` already gitignored.

## Goals / Non-Goals

**Goals:**

- Runnable `backend/` skeleton following KB 08 §2 with layered separation enforceable by imports (`api` → `services` → `models`).
- One-command local DB (`docker compose up db`) + versioned migrations from empty state.
- Env-driven config with committed `.env.example`; fail-fast on missing required vars.
- pytest harness with isolated test DB proving `/health` + DB round-trip.

**Non-Goals:**

- Domain models, auth, business endpoints (C-02+). No production/staging deploy config. No frontend scaffolding.

## Decisions

- **Async SQLAlchemy 2.0 + `asyncpg` over sync.** KB mandates async FastAPI; async engine matches the runtime. Alternative (sync + `psycopg2`) is simpler with Alembic but forces sync endpoints and a later rewrite — rejected.
- **Alembic with async-compatible `env.py`** (run migrations via async engine). Alternative of sync URL just for migrations creates two connection paths and drift — rejected; single async path with `asyncio.run` in `env.py`.
- **Declarative `Base` + session factory in `app/core/database.py`, Settings in `app/core/config.py` (Pydantic Settings).** Keeps tenant/UTC helpers in one place for C-02 to extend (`clinic_id` mixin, UTC `DateTime` default). Alternative of scattering engine creation per module — rejected (duplication, untestable).
- **Compose: single `db` (PostgreSQL 16) + test DB as separate database on the same service** (`POSTGRES_DB` vs `TEST_DATABASE_URL`), not a second container. Cheaper, no port conflicts; CI can use a service container identically.
- **Test isolation via per-test transaction rollback + dependency override** of the session dependency, not truncate-all. Faster and parallel-safe; Alembic upgrade runs once per session.

## Risks / Trade-offs

- [Risk] `asyncpg` + Alembic autogenerate quirks → Mitigation: smoke-test `upgrade head`/`downgrade -1` on empty DB in C-01 acceptance; pin driver versions.
- [Risk] Dev without Docker (no Compose) can't run DB → Mitigation: document Docker as prerequisite; `TEST_DATABASE_URL` allows pointing at any Postgres.
- [Risk] Timezone bugs later (local vs UTC) → Mitigation: establish UTC-only storage convention now; no local-time conversion helpers in backend (UI-only per RN-07).

## Migration Plan

Greenfield: no data to migrate. Rollback = delete `backend/` + compose file (no production state exists).

## Open Questions

None blocking. Python/FastAPI/SQLAlchemy minor versions pinned at implementation time from current stable (recorded in `requirements.txt` by the apply step).
