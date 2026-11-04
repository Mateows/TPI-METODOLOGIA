"""Task 3.1 — async engine/session/Base/get_db with a round-trip test.

Runs against an in-memory SQLite database so it is green without Docker;
the same code path serves PostgreSQL (asyncpg) via DATABASE_URL.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text


def _fresh_db():
    import importlib

    import app.core.config as config
    import app.core.database as db

    importlib.reload(config)
    return importlib.reload(db)


@pytest.fixture()
def sqlite_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    return "sqlite+aiosqlite:///:memory:"


async def test_session_round_trip_opens_and_closes(sqlite_url):
    """A session opens, runs SELECT 1, and closes cleanly."""
    db = _fresh_db()
    async with db.SessionLocal() as session:
        value = (await session.execute(text("SELECT 1"))).scalar()
    assert value == 1


async def test_get_db_yields_usable_session_then_closes(sqlite_url):
    """get_db dependency yields a session the API can use per request."""
    db = _fresh_db()
    agen = db.get_db()
    session = await agen.__anext__()
    assert (await session.execute(text("SELECT 1"))).scalar() == 1
    try:
        await agen.__anext__()
    except StopAsyncIteration:
        pass
    else:  # pragma: no cover
        raise AssertionError("get_db must yield exactly once")


def test_base_metadata_registers_core_models():
    """Task 2.3 / C-03 1.1: importing app.models registers clinics/users/refresh_tokens/patients."""
    import app.models as models
    from app.models import Clinic, Patient, RefreshToken, User

    metadata = models.Clinic.metadata
    assert hasattr(metadata, "tables")
    assert {"clinics", "users", "refresh_tokens", "patients"} <= set(metadata.tables)
    assert metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert {
        Clinic.__tablename__,
        User.__tablename__,
        RefreshToken.__tablename__,
        Patient.__tablename__,
    } <= set(metadata.tables)
    assert set(models.__all__) == {
        "Clinic",
        "Patient",
        "RefreshToken",
        "USER_ROLES",
        "User",
    }
