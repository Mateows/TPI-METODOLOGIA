"""Async SQLAlchemy 2.0 wiring (single connection path for app + Alembic).

Extension points for C-02: `clinic_id` tenant mixin on Base subclasses and
UTC-only DateTime defaults. All timestamps persist in UTC; conversion to
America/Argentina/Buenos_Aires happens only in the UI layer (RN-07).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Deterministic names for every index/constraint so Alembic autogenerate does
# not emit spurious DDL and both PostgreSQL and SQLite stay in sync (design D9).
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Timezone-aware UTC now. All timestamps persist in UTC (RN-07)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative registry every domain model (C-02+) registers on."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, always closed."""
    async with SessionLocal() as session:
        yield session
