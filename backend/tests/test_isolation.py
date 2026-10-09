"""Task 5.1 — marker test: the suite writes ONLY to the isolated test database."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError


async def test_marker_write_lands_only_in_test_database(test_session, dev_engine, test_settings):
    """A write through the test session is visible in test DB, absent in dev DB."""
    assert test_settings.TEST_DATABASE_URL != test_settings.DATABASE_URL
    await test_session.execute(
        text("CREATE TABLE IF NOT EXISTS _foundation_probe (marker TEXT PRIMARY KEY)")
    )
    await test_session.execute(text("DELETE FROM _foundation_probe"))
    await test_session.execute(
        text("INSERT INTO _foundation_probe (marker) VALUES ('C01-PROBE-001')")
    )
    rows = (await test_session.execute(text("SELECT marker FROM _foundation_probe"))).scalars().all()
    assert "C01-PROBE-001" in rows

    async with dev_engine.connect() as conn:
        with pytest.raises((OperationalError, DBAPIError)):
            await conn.execute(text("SELECT marker FROM _foundation_probe"))


async def test_client_health_runs_against_test_database(client):
    """The overridden API client serves /health from the test database."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "healthy"
