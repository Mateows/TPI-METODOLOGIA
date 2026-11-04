"""Task 2.2 / C-03 1.2 — Alembic chain reaches 0003 and is repeatable both ways."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
HEAD_REVISION = "0003_patient_management"
PREVIOUS_REVISION = "0002_core_models_tenants"
BASE_REVISION = "0001_init"
CORE_TABLES = {"clinics", "users", "refresh_tokens", "patients"}


def _alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k in ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP")
    }
    env.update(
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        TEST_DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        SECRET_KEY="test-secret",
        ALEMBIC_DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    return {name for (name,) in rows}


def test_env_py_is_async_and_wired_to_base_metadata():
    """env.py must use the single async path against Base.metadata."""
    body = (BACKEND_DIR / "alembic" / "env.py").read_text()
    assert "asyncio.run" in body
    assert "run_sync" in body
    assert "Base.metadata" in body
    assert "ALEMBIC_DATABASE_URL" in body
    assert "import app.models" in body  # registers tables on Base.metadata
    assert "create_engine(" not in body  # no sync second path (design decision)


def test_upgrade_head_creates_core_tables(tmp_path):
    """WHEN upgrading an empty DB THEN clinics/users/refresh_tokens/patients exist."""
    db_path = tmp_path / "core.db"
    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, upgrade.stderr
    assert CORE_TABLES <= _tables(db_path)


def test_migration_chain_is_ordered_and_repeatable(tmp_path):
    """upgrade head → downgrade 0002 → upgrade head → downgrade 0001 → upgrade head."""
    db_path = tmp_path / "migra.db"
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)

    downgrade_0002 = _alembic("downgrade", PREVIOUS_REVISION, db_path=db_path)
    assert downgrade_0002.returncode == 0, downgrade_0002.stderr
    assert "patients" not in _tables(db_path)
    assert {"clinics", "users", "refresh_tokens"} <= _tables(db_path)

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)

    downgrade_0001 = _alembic("downgrade", BASE_REVISION, db_path=db_path)
    assert downgrade_0001.returncode == 0, downgrade_0001.stderr
    assert not (CORE_TABLES & _tables(db_path))

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)

    second_upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert second_upgrade.returncode == 0  # no-op on up-to-date DB

    heads = _alembic("heads", db_path=db_path)
    assert heads.returncode == 0 and HEAD_REVISION in heads.stdout


def test_alembic_check_reports_no_pending_model_changes(tmp_path):
    """Metadata matches migrated schema: nothing left to autogenerate."""
    db_path = tmp_path / "check.db"
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    check = _alembic("check", db_path=db_path)
    assert check.returncode == 0, check.stderr
