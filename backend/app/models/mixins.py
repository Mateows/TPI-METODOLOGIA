"""Reusable column mixins for domain models (design D9).

UUID primary keys and UTC timestamps are shared by every C-02 entity so the
schema stays portable between PostgreSQL (canonical) and SQLite (harness).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import utcnow


class UuidPrimaryKeyMixin:
    """UUID v4 primary key generated in the application layer."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, nullable=False
    )


class TimestampMixin:
    """Creation/update timestamps persisted in UTC (RN-07)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
