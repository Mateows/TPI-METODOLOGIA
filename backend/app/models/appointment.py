"""``Appointment``: an agenda appointment owned by exactly one clinic (design D1/D3/D4).

A clinic appointment links a patient, dentist (user with role 'dentist'), and a box.
Statuses: scheduled, confirmed, attended, cancelled, no_show.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.box import Box
    from app.models.clinic import Clinic
    from app.models.patient import Patient
    from app.models.user import User

APPOINTMENT_STATUSES: tuple[str, ...] = (
    "scheduled",
    "confirmed",
    "attended",
    "cancelled",
    "no_show",
)


class Appointment(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Clinic-owned appointment; ``clinic_id`` is always server-derived."""

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'attended', 'cancelled', 'no_show')",
            name="status",
        ),
        Index(
            "ix_appointments_clinic_dentist_start",
            "clinic_id",
            "dentist_id",
            "start_time",
        ),
        Index(
            "ix_appointments_clinic_box_start",
            "clinic_id",
            "box_id",
            "start_time",
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    dentist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    box_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("boxes.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    clinic: Mapped[Clinic] = relationship("Clinic")
    patient: Mapped[Patient] = relationship("Patient")
    dentist: Mapped[User] = relationship("User")
    box: Mapped[Box] = relationship("Box")
