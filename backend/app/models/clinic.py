"""Clinic (tenant root) — every clinic-owned record scopes to ``clinics.id``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids runtime import cycle
    from app.models.user import User


class Clinic(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant boundary (RN-02). ``slug`` is reserved for the public portal (D7)."""

    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tax_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list[User]] = relationship(
        "User", back_populates="clinic", cascade="all, delete-orphan"
    )
