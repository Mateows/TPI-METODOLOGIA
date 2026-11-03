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
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.clinic import Clinic
    from app.models.user import User

BACKEND_DIR = Path(__file__).resolve().parents[1]
_TMP = Path(tempfile.gettempdir())

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / 'tpi_foundation_dev.db'}")
os.environ.setdefault(
    "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / 'tpi_foundation_test.db'}"
)
os.environ.setdefault("SECRET_KEY", "test-secret-foundation-harness")


def _iter_dependency_calls(dependant):
    """Yield every callable a FastAPI route depends on, transitively."""
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _iter_dependency_calls(dependency)


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
    # ``tests/test_health.py`` reloads ``app.core.database``, which creates a new
    # ``get_db`` object while routers keep the one captured by ``Depends`` at
    # import time. Override every ``get_db`` wired into the app so the isolated
    # test session is always used, regardless of module state.
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        for call in _iter_dependency_calls(dependant):
            if (
                getattr(call, "__module__", "") == "app.core.database"
                and getattr(call, "__name__", "") == "get_db"
            ):
                app.dependency_overrides[call] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


@dataclass
class SeededTenant:
    """A clinic + user pair created inside the current test transaction."""

    clinic: Clinic
    user: User

    def token(self, *, clinic_id: str | None = None, expires_delta: timedelta | None = None) -> str:
        from app.core.security import create_access_token

        return create_access_token(
            subject=str(self.user.id),
            clinic_id=clinic_id or str(self.clinic.id),
            role=self.user.role,
            expires_delta=expires_delta,
        )


@pytest.fixture()
async def seed_tenant(test_session):
    """Factory fixture: clone-safe clinic/user seeding for auth tests."""
    from app.core.security import hash_password
    from app.models.clinic import Clinic
    from app.models.user import User

    counter = {"n": 0}

    async def _seed(
        *,
        email: str | None = None,
        role: str = "admin",
        password: str = "Secreta-123",
        clinic_name: str | None = None,
        clinic_slug: str | None = None,
        tax_id: str | None = None,
        clinic_active: bool = True,
        user_active: bool = True,
    ) -> SeededTenant:
        counter["n"] += 1
        index = counter["n"]
        clinic = Clinic(
            name=clinic_name or f"Clinica {index}",
            slug=clinic_slug or f"clinica-{index}-{uuid.uuid4().hex[:8]}",
            tax_id=tax_id or f"30-{index:08d}-1",
            is_active=clinic_active,
        )
        test_session.add(clinic)
        await test_session.flush()

        user = User(
            clinic_id=clinic.id,
            email=email or f"user{index}@example.com",
            password_hash=hash_password(password),
            full_name=f"Usuario {index}",
            role=role,
            is_active=user_active,
        )
        test_session.add(user)
        await test_session.flush()
        return SeededTenant(clinic=clinic, user=user)

    return _seed
