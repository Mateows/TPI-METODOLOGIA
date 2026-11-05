"""Environment-driven configuration (fail-fast on missing required vars).

All datetimes are persisted in UTC; conversion to America/Argentina/Buenos_Aires
happens only in the UI layer (RN-07). Never log SECRET_KEY or patient data
(Ley 25.326 logging prohibition).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Required vars have no defaults: a missing variable raises
    pydantic ValidationError naming it at import time (fail-fast)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    DATABASE_URL: str
    TEST_DATABASE_URL: str
    SECRET_KEY: SecretStr

    # Token lifetimes (design D2/D3). Out-of-range values fail at import time
    # instead of silently issuing unusably short or dangerously long sessions.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    # Operator bootstrap password (design D8); never required to boot, never
    # logged. Falls back to a hidden prompt in app.cli.bootstrap_clinic.
    BOOTSTRAP_ADMIN_PASSWORD: SecretStr | None = None

    WHATSAPP_API_TOKEN: str | None = None
    AFIP_CERT_PATH: str | None = None
    AFIP_CUIT: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
