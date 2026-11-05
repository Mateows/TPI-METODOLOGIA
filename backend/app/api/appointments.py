"""Clinic-scoped appointments router: ``/api/v1/appointments``.

All endpoints require an authenticated clinic staff member (admin, receptionist, dentist)
and automatically scope reads and writes to ``principal.clinic_id``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.appointments import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentStatusUpdateRequest,
)
from app.services import appointments as appointments_service
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

StaffGuard = Annotated[
    Principal, Depends(require_roles("admin", "receptionist", "dentist"))
]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    payload: AppointmentCreateRequest,
    principal: StaffGuard,
    db: DbSession,
) -> AppointmentResponse:
    """Schedule a new appointment for the caller's clinic."""
    async with appointments_service.appointment_resource_lock(
        principal.clinic_id, payload.dentist_id, payload.box_id
    ):
        appointment = await appointments_service.create_appointment(db, principal, payload)
        await db.commit()
        return AppointmentResponse.model_validate(appointment)


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    principal: StaffGuard,
    db: DbSession,
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[AppointmentResponse]:
    """List appointments for the caller's clinic with optional date range and status filters."""
    appointments = await appointments_service.list_appointments(
        db, principal, start_time=start_time, end_time=end_time, status=status
    )
    return [AppointmentResponse.model_validate(a) for a in appointments]


@router.get("/{id}", response_model=AppointmentResponse)
async def get_appointment(
    id: uuid.UUID,
    principal: StaffGuard,
    db: DbSession,
) -> AppointmentResponse:
    """Retrieve an appointment by ID."""
    appointment = await appointments_service.get_appointment(db, principal, id)
    return AppointmentResponse.model_validate(appointment)


@router.patch("/{id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    id: uuid.UUID,
    payload: AppointmentStatusUpdateRequest,
    principal: StaffGuard,
    db: DbSession,
) -> AppointmentResponse:
    """Update an appointment's status according to the transition matrix."""
    appointment = await appointments_service.update_appointment_status(
        db, principal, id, payload
    )
    await db.commit()
    return AppointmentResponse.model_validate(appointment)
