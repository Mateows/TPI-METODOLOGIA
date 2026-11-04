"""Patient model: clinic-scoped individual with JSON anamnesis summary (D1/D2)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.clinic import Clinic


class Patient(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Clinic-scoped patient record (RN-02). DNI is unique per clinic (D1)."""

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "dni"),
        Index(
            "ix_patients_clinic_id_last_name_first_name",
            "clinic_id",
            "last_name",
            "first_name",
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dni: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    medical_history_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clinic: Mapped[Clinic] = relationship("Clinic")

    @validates("email")
    def _normalize_email(self, _key: str, value: str | None) -> str | None:
        """Store non-empty emails lowercased and stripped."""
        if value is None:
            return None
        stripped = value.strip().lower()
        return stripped or None
