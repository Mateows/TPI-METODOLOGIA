"""User account: a person operating inside exactly one clinic (D6/D12)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.clinic import Clinic
    from app.models.refresh_token import RefreshToken

# Closed role set (knowledge-base/03). ``dentist`` is the agenda professional
# (design D12); there is no separate Professional entity.
USER_ROLES: tuple[str, ...] = ("admin", "receptionist", "dentist")


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Clinic-scoped identity. Email is globally unique (design D6)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'receptionist', 'dentist')", name="role"
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clinic: Mapped[Clinic] = relationship("Clinic", back_populates="users")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """Store emails lowercased so uniqueness is effectively case-insensitive."""
        return value.strip().lower()
