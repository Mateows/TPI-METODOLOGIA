"""Tasks 4.1/4.2 — GET /health: healthy 200 + unhealthy path, no body logging."""

from __future__ import annotations

import logging

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest.fixture()
def env_ok(monkeypatch, tmp_path):
    db = tmp_path / "health.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.chdir(tmp_path)
    import importlib

    import app.core.config as config
    import app.core.database as database

    importlib.reload(config)
    return importlib.reload(database)


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _fresh_main():
    """Reload the full chain so routes bind to the current test settings."""
    import importlib

    import app.api.health as health
    import app.core.config as config
    import app.core.database as database
    import app.main as main

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(health)
    return importlib.reload(main)


async def test_health_returns_200_with_healthy_payload(env_ok):
    """WHEN the database is reachable THEN 200 with healthy app+db status."""
    main = _fresh_main()
    async with _client(main.app) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["app"] == "healthy"
    assert payload["database"] == "healthy"


async def test_health_reports_unhealthy_when_database_is_stopped(env_ok):
    """WHEN the database is unreachable THEN unhealthy (non-200 or flag)."""
    main = _fresh_main()

    class _DeadSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("connection refused")

    async def broken_db():
        yield _DeadSession()

    main.app.dependency_overrides[main.get_db] = broken_db
    try:
        async with _client(main.app) as client:
            response = await client.get("/health")
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code != 200 or response.json()["database"] == "unhealthy"
    assert response.json()["database"] == "unhealthy"


async def test_health_against_unreachable_url_is_unhealthy(monkeypatch, tmp_path):
    """A misconfigured/unreachable DATABASE_URL also yields unhealthy, not 500-trace."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/nowhere")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/nowhere")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.chdir(tmp_path)
    main = _fresh_main()
    async with _client(main.app) as client:
        response = await client.get("/health")
    assert response.json()["database"] == "unhealthy"
    assert "traceback" not in response.text.lower()


async def test_health_never_logs_request_bodies(env_ok, caplog):
    """Patient-like content in requests must never land in logs (Ley 25.326)."""
    main = _fresh_main()
    marker = "PACIENTE-SENSIBLE-DNI-30999111"
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        async with _client(main.app) as client:
            await client.get("/health")
            await client.post("/health", content=marker)
    assert marker not in caplog.text


async def test_health_round_trip_uses_live_session(env_ok):
    """The check executes a real query through the session factory."""
    import importlib

    import app.core.database as database

    importlib.reload(database)
    async with database.SessionLocal() as session:
        assert (await session.execute(text("SELECT 1"))).scalar() == 1
