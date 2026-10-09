"""Async SQLAlchemy 2.0 wiring (single connection path for app + Alembic).

Extension points for C-02: `clinic_id` tenant mixin on Base subclasses and
UTC-only DateTime defaults. All timestamps persist in UTC; conversion to
America/Argentina/Buenos_Aires happens only in the UI layer (RN-07).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative registry every domain model (C-02+) registers on."""


engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, always closed."""
    async with SessionLocal() as session:
        yield session
