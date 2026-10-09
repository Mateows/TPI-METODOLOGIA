"""Task 2.1 — config boots from env, fails fast naming the missing variable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _clean_env() -> dict[str, str]:
    """Minimal env that cannot provide settings via OS or .env files."""
    keep = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "PYTHONUTF8")
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PYTHONUTF8"] = "1"
    return env


def _import_settings_source() -> str:
    return "from app.core.config import settings; print(settings.DATABASE_URL)"


def test_boot_with_valid_configuration(tmp_path, monkeypatch):
    """WHEN all required env vars are set THEN the app config becomes ready."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/devdb")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/testdb")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.chdir(tmp_path)  # no .env can leak in

    import importlib

    import app.core.config as config

    importlib.reload(config)
    assert config.settings.DATABASE_URL == "postgresql+asyncpg://u:p@localhost:5432/devdb"
    assert config.settings.SECRET_KEY.get_secret_value() == "test-secret"


def test_missing_database_url_fails_fast_naming_variable(tmp_path):
    """WHEN DATABASE_URL is absent THEN import fails naming DATABASE_URL."""
    proc = subprocess.run(
        [sys.executable, "-c", _import_settings_source()],
        cwd=tmp_path,
        env=_clean_env() | {"PYTHONPATH": str(BACKEND_DIR)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode != 0
    assert "DATABASE_URL" in proc.stderr


def test_missing_secret_key_fails_fast_naming_variable(tmp_path):
    """WHEN SECRET_KEY is absent THEN import fails naming SECRET_KEY."""
    proc = subprocess.run(
        [sys.executable, "-c", _import_settings_source()],
        cwd=tmp_path,
        env=_clean_env()
        | {
            "PYTHONPATH": str(BACKEND_DIR),
            "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/devdb",
            "TEST_DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/testdb",
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode != 0
    assert "SECRET_KEY" in proc.stderr


def test_optional_integration_vars_default_to_none(monkeypatch, tmp_path):
    """Optional WhatsApp/AFIP placeholders must not be required to boot."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/devdb")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/testdb")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    for var in ("WHATSAPP_API_TOKEN", "AFIP_CERT_PATH", "AFIP_CUIT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)

    import importlib

    import app.core.config as config

    importlib.reload(config)
    assert config.settings.WHATSAPP_API_TOKEN is None
    assert config.settings.AFIP_CERT_PATH is None
    assert config.settings.AFIP_CUIT is None
