"""Task 3.2 — docker-compose.yml structure (static; live `up -d` needs Docker).

Live verification (`docker compose up -d db` reaching healthy) is documented
in task 5.2 and runs on machines with Docker; these tests pin the contract.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"


def _body() -> str:
    return COMPOSE.read_text()


def test_compose_defines_postgres16_with_volume_and_healthcheck():
    body = _body()
    assert "postgres:16" in body
    assert "pgdata:/var/lib/postgresql/data" in body
    assert "healthcheck" in body
    assert "pg_isready" in body


def test_compose_provisions_dev_and_test_databases():
    body = _body()
    assert "POSTGRES_DB" in body
    assert "POSTGRES_TEST_DB" in body
    assert "init-test-db" in body  # init script creating the test DB on first boot


def test_env_example_matches_compose_postgres_keys():
    example = (ROOT / ".env.example").read_text()
    for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_TEST_DB"):
        assert key in example
        assert key in _body()
