"""Shared pytest harness (task 5.1): isolated test DB, per-test rollback.

Defaults target file SQLite databases so the suite is green without Docker.
With Docker, export DATABASE_URL / TEST_DATABASE_URL (PostgreSQL + asyncpg)
and every fixture below uses them unchanged — including the session-scoped
Alembic upgrade.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
_TMP = Path(tempfile.gettempdir())

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / 'tpi_foundation_dev.db'}")
os.environ.setdefault(
    "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / 'tpi_foundation_test.db'}"
)
os.environ.setdefault("SECRET_KEY", "test-secret-foundation-harness")


@pytest.fixture(scope="session")
def test_settings():
    from app.core.config import settings as loaded

    assert loaded.TEST_DATABASE_URL != loaded.DATABASE_URL, (
        "TEST_DATABASE_URL must never equal DATABASE_URL (dev/test isolation)"
    )
    return loaded


@pytest.fixture(scope="session", autouse=True)
def _alembic_upgrade_test_db(test_settings):
    """Alembic migrates the isolated test database once per session."""
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = test_settings.TEST_DATABASE_URL
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.fixture()
async def test_engine(test_settings, _alembic_upgrade_test_db):
    engine = create_async_engine(test_settings.TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def dev_engine(test_settings):
    engine = create_async_engine(test_settings.DATABASE_URL, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def test_session(test_engine):
    """One transaction per test, always rolled back — never commits to any DB."""
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture()
async def client(test_session):
    """Async API client with the session dependency overridden to test_session."""
    from app.core.database import get_db
    from app.main import app

    async def _override():
        yield test_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
