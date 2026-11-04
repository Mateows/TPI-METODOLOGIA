"""Task 3.3 — async Alembic env wired to Base.metadata; chain is repeatable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
<<<<<<< Updated upstream
=======
HEAD_REVISION = "0003_boxes"
BASE_REVISION = "0001_init"
CORE_REVISION = "0002_core_models_tenants"
CORE_TABLES = {"clinics", "users", "refresh_tokens"}
BOXES_TABLES = {"boxes"}
>>>>>>> Stashed changes


def _alembic(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP")}
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


def test_env_py_is_async_and_wired_to_base_metadata():
    """env.py must use the single async path against Base.metadata."""
    body = (BACKEND_DIR / "alembic" / "env.py").read_text()
    assert "asyncio.run" in body
    assert "run_sync" in body
    assert "Base.metadata" in body
    assert "ALEMBIC_DATABASE_URL" in body
    assert "create_engine(" not in body  # no sync second path (design decision)


<<<<<<< Updated upstream
=======
def test_upgrade_head_creates_core_tables(tmp_path):
    """WHEN upgrading an empty DB THEN clinics/users/refresh_tokens exist."""
    db_path = tmp_path / "core.db"
    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, upgrade.stderr
    assert CORE_TABLES <= _tables(db_path)


def test_upgrade_head_creates_boxes_and_downgrade_to_core_drops_them(tmp_path):
    """WHEN upgrading an empty DB THEN boxes exists; downgrading 0002 removes it."""
    db_path = tmp_path / "boxes.db"
    upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert upgrade.returncode == 0, upgrade.stderr
    assert BOXES_TABLES <= _tables(db_path)

    downgrade = _alembic("downgrade", CORE_REVISION, db_path=db_path)
    assert downgrade.returncode == 0, downgrade.stderr
    assert not (BOXES_TABLES & _tables(db_path))
    assert CORE_TABLES <= _tables(db_path)

    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    assert BOXES_TABLES <= _tables(db_path)


>>>>>>> Stashed changes
def test_migration_chain_is_ordered_and_repeatable(tmp_path):
    """upgrade head → downgrade -1 → upgrade head leaves zero pending revisions."""
    db_path = tmp_path / "migra.db"
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    downgrade = _alembic("downgrade", "-1", db_path=db_path)
    assert downgrade.returncode == 0
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    second_upgrade = _alembic("upgrade", "head", db_path=db_path)
    assert second_upgrade.returncode == 0  # no-op on up-to-date DB
    heads = _alembic("heads", db_path=db_path)
    assert heads.returncode == 0 and "0001_init" in heads.stdout


def test_alembic_check_reports_no_pending_model_changes(tmp_path):
    """Metadata matches migrated schema: nothing left to autogenerate."""
    db_path = tmp_path / "check.db"
    assert _alembic("upgrade", "head", db_path=db_path).returncode == 0
    check = _alembic("check", db_path=db_path)
    assert check.returncode == 0, check.stderr
