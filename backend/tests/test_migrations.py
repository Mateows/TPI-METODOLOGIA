"""C-02/C-03/C-04 — async Alembic env wired to Base.metadata; chain is repeatable.

La cadena queda lineal: 0001_init → 0002_core_models_tenants →
0003_patient_management → 0004_boxes.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
HEAD_REVISION = "0005_appointments"
BOXES_REVISION = "0004_boxes"
PATIENTS_REVISION = "0003_patient_management"
CORE_REVISION = "0002_core_models_tenants"
BASE_REVISION = "0001_init"
CORE_TABLES = {"clinics", "users", "refresh_tokens", "patients"}
BOXES_TABLES = {"boxes"}
APPOINTMENTS_TABLES = {"appointments"}


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


def test_upgrade_head_creates_boxes_and_downgrade_to_patients_drops_them(tmp_path):
    """WHEN upgrading an empty DB THEN boxes exists; downgrading 0003 removes it."""
    db_path = tmp_path / "boxes.db"
    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, upgrade.stderr
    assert BOXES_TABLES <= _tables(db_path)

    downgrade = _alembic("downgrade", PATIENTS_REVISION, db_path=db_path)
    assert downgrade.returncode == 0, downgrade.stderr
    assert not (BOXES_TABLES & _tables(db_path))
    assert CORE_TABLES <= _tables(db_path)

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert BOXES_TABLES <= _tables(db_path)


def test_upgrade_head_creates_appointments_and_downgrade_to_boxes_drops_them(tmp_path):
    """WHEN upgrading an empty DB THEN appointments exists; downgrading 0004 removes it."""
    db_path = tmp_path / "appointments.db"
    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, upgrade.stderr
    assert APPOINTMENTS_TABLES <= _tables(db_path)

    downgrade = _alembic("downgrade", BOXES_REVISION, db_path=db_path)
    assert downgrade.returncode == 0, downgrade.stderr
    assert not (APPOINTMENTS_TABLES & _tables(db_path))
    assert BOXES_TABLES <= _tables(db_path)

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert APPOINTMENTS_TABLES <= _tables(db_path)


def test_migration_chain_is_ordered_and_repeatable(tmp_path):
    """upgrade head → downgrade 0004 → 0003 → 0002 → 0001 → upgrade head (ida y vuelta)."""
    db_path = tmp_path / "migra.db"
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)
    assert BOXES_TABLES <= _tables(db_path)
    assert APPOINTMENTS_TABLES <= _tables(db_path)

    downgrade_0004 = _alembic("downgrade", BOXES_REVISION, db_path=db_path)
    assert downgrade_0004.returncode == 0, downgrade_0004.stderr
    assert "appointments" not in _tables(db_path)
    assert BOXES_TABLES <= _tables(db_path)

    downgrade_0003 = _alembic("downgrade", PATIENTS_REVISION, db_path=db_path)
    assert downgrade_0003.returncode == 0, downgrade_0003.stderr
    assert "boxes" not in _tables(db_path)
    assert CORE_TABLES <= _tables(db_path)

    down_to_core = _alembic("downgrade", CORE_REVISION, db_path=db_path)
    assert down_to_core.returncode == 0, down_to_core.stderr
    assert "patients" not in _tables(db_path)
    assert {"clinics", "users", "refresh_tokens"} <= _tables(db_path)

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)
    assert BOXES_TABLES <= _tables(db_path)
    assert APPOINTMENTS_TABLES <= _tables(db_path)

    downgrade_0001 = _alembic("downgrade", BASE_REVISION, db_path=db_path)
    assert downgrade_0001.returncode == 0, downgrade_0001.stderr
    assert not (CORE_TABLES & _tables(db_path))
    assert not (BOXES_TABLES & _tables(db_path))
    assert not (APPOINTMENTS_TABLES & _tables(db_path))

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert CORE_TABLES <= _tables(db_path)
    assert BOXES_TABLES <= _tables(db_path)
    assert APPOINTMENTS_TABLES <= _tables(db_path)

    second_upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert second_upgrade.returncode == 0  # no-op on up-to-date DB

    check = _alembic("check", db_path=db_path)
    assert check.returncode == 0, check.stdout + check.stderr

    heads = _alembic("heads", db_path=db_path)
    assert heads.returncode == 0
    assert HEAD_REVISION in heads.stdout
    assert heads.stdout.count("(head)") == 1  # una sola cabeza, sin ramas
