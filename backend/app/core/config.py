"""Environment-driven configuration (fail-fast on missing required vars).

All datetimes are persisted in UTC; conversion to America/Argentina/Buenos_Aires
happens only in the UI layer (RN-07). Never log SECRET_KEY or patient data
(Ley 25.326 logging prohibition).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
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

    WHATSAPP_API_TOKEN: str | None = None
    AFIP_CERT_PATH: str | None = None
    AFIP_CUIT: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
