"""Task 2.1 — config boots from env, fails fast naming the missing variable."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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


def _boot_env() -> dict[str, str]:
    return {
        "PYTHONPATH": str(BACKEND_DIR),
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/devdb",
        "TEST_DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/testdb",
        "SECRET_KEY": "test-secret",
    }


def _boot_proc(tmp_path, **overrides: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _import_settings_source()],
        cwd=tmp_path,
        env=_clean_env() | _boot_env() | overrides,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_token_lifetimes_have_safe_defaults(monkeypatch, tmp_path):
    """WHEN lifetimes are absent THEN 15-minute access / 7-day refresh."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/devdb")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/testdb")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)
    monkeypatch.chdir(tmp_path)

    import importlib

    import app.core.config as config

    importlib.reload(config)
    assert config.settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert config.settings.REFRESH_TOKEN_EXPIRE_DAYS == 7


@pytest.mark.parametrize(
    ("variable", "invalid"),
    [
        ("ACCESS_TOKEN_EXPIRE_MINUTES", "0"),
        ("ACCESS_TOKEN_EXPIRE_MINUTES", "1441"),
        ("REFRESH_TOKEN_EXPIRE_DAYS", "0"),
        ("REFRESH_TOKEN_EXPIRE_DAYS", "91"),
    ],
)
def test_out_of_range_token_lifetime_blocks_boot(tmp_path, variable, invalid):
    """WHEN a token lifetime is outside its range THEN import fails naming it."""
    proc = _boot_proc(tmp_path, **{variable: invalid})
    assert proc.returncode != 0
    assert variable in proc.stderr


def test_bootstrap_admin_password_is_optional_and_secret(monkeypatch, tmp_path):
    """Bootstrap runs from env/prompt (D8): absent by default, never plaintext."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/devdb")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/testdb")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)

    import importlib

    import app.core.config as config

    importlib.reload(config)
    assert config.settings.BOOTSTRAP_ADMIN_PASSWORD is None

    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "bootstrap-secret")
    importlib.reload(config)
    assert config.settings.BOOTSTRAP_ADMIN_PASSWORD is not None
    assert (
        config.settings.BOOTSTRAP_ADMIN_PASSWORD.get_secret_value()
        == "bootstrap-secret"
    )


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
