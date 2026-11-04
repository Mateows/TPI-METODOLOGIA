"""``Box``: an agenda resource owned by exactly one clinic (design D3).

A box carries a closed status set. ``maintenance`` does not block scheduling in
C-04: ``design.md`` §Open Questions (3) is still open.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin

# Closed status set (knowledge-base/04). ``active`` is the creation default.
BOX_STATUSES: tuple[str, ...] = ("active", "maintenance")


class Box(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Clinic-owned agenda box; ``clinic_id`` is always server-derived."""

    __tablename__ = "boxes"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'maintenance')", name="status"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
