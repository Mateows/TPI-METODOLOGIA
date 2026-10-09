"""Task 2.2 — .env.example covers every required Settings key, no secrets."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"


def _example_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def test_env_example_covers_all_required_settings_keys(monkeypatch):
    """Diff of required keys between config.py and .env.example: no missing key."""
    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setenv("TEST_DATABASE_URL", "y")
    monkeypatch.setenv("SECRET_KEY", "z")
    from app.core.config import Settings

    required = {
        name
        for name, field in Settings.model_fields.items()
        if field.is_required()
    }
    assert required == {"DATABASE_URL", "TEST_DATABASE_URL", "SECRET_KEY"}
    assert required <= _example_keys(), f"missing: {required - _example_keys()}"


def test_env_example_documents_optional_integration_keys():
    """Optional placeholders (WhatsApp/AFIP) must be documented too."""
    assert {"WHATSAPP_API_TOKEN", "AFIP_CERT_PATH", "AFIP_CUIT"} <= _example_keys()


def test_env_example_contains_no_real_secrets():
    """Committed example must hold placeholders, never credential-looking values."""
    body = ENV_EXAMPLE.read_text()
    assert "change-me" in body  # placeholder marker for SECRET_KEY
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("SECRET_KEY="):
            value = stripped.split("=", 1)[1]
            assert len(value) < 64 or "change-me" in value
