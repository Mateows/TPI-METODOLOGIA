"""Pydantic schemas for appointments (/api/v1/appointments).

All incoming schemas forbid extra fields (extra="forbid") so any client attempting
to pass `clinic_id` is automatically rejected with HTTP 422 validation_error.
All datetime fields must be timezone-aware (naive datetimes rejected with HTTP 422).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import APPOINTMENT_STATUSES


def _check_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime must be timezone-aware")
    return value


class AppointmentCreateRequest(BaseModel):
    """Payload to create an appointment. clinic_id is server-derived only."""

    model_config = ConfigDict(extra="forbid")

    patient_id: uuid.UUID
    dentist_id: uuid.UUID
    box_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("start_time", "end_time")
    @classmethod
    def _validate_tz(cls, value: datetime) -> datetime:
        return _check_timezone_aware(value)


class AppointmentStatusUpdateRequest(BaseModel):
    """Payload to transition appointment status."""

    model_config = ConfigDict(extra="forbid")

    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        if value not in APPOINTMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(APPOINTMENT_STATUSES)}")
        return value


class AppointmentResponse(BaseModel):
    """Response view of an appointment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    dentist_id: uuid.UUID
    box_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
