"""Appointment business service (C-04).

Orchestrates multi-tenant verification, date & timezone validations (RN-07),
overlap prevention (RN-01), and state machine transitions.
Does not commit: the API router owns the transaction boundary.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AppointmentNotFound,
    AppointmentOverlap,
    BoxNotFound,
    DentistNotFound,
    InvalidAppointmentTransition,
    InvalidTimeRange,
    PatientNotFound,
)
from app.models.appointment import Appointment
from app.repositories.appointments import AppointmentRepository
from app.repositories.boxes import BoxRepository
from app.repositories.patients import PatientRepository
from app.repositories.users import UserRepository
from app.schemas.appointments import (
    AppointmentCreateRequest,
    AppointmentStatusUpdateRequest,
)
from app.services.principal import Principal

# Allowed status transitions (knowledge-base/07 & spec)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"confirmed", "cancelled"},
    "confirmed": {"attended", "cancelled"},
}

_RESOURCE_LOCKS: dict[tuple[uuid.UUID, str, uuid.UUID], asyncio.Lock] = defaultdict(asyncio.Lock)
_RESOURCE_LOCKS_MUTEX = asyncio.Lock()


async def _get_resource_lock(key: tuple[uuid.UUID, str, uuid.UUID]) -> asyncio.Lock:
    async with _RESOURCE_LOCKS_MUTEX:
        return _RESOURCE_LOCKS[key]


@contextlib.asynccontextmanager
async def appointment_resource_lock(
    clinic_id: uuid.UUID, dentist_id: uuid.UUID, box_id: uuid.UUID
):
    """Serialize booking requests for the same dentist or box within a clinic.

    Portable concurrency mechanism that guarantees in-process serialization
    across concurrent booking attempts, preventing race conditions before
    transaction isolation and PostgreSQL EXCLUDE constraints apply.
    """
    keys = sorted([
        (clinic_id, "box", box_id),
        (clinic_id, "dentist", dentist_id),
    ])
    locks = [await _get_resource_lock(k) for k in keys]
    async with contextlib.AsyncExitStack() as stack:
        for lock in locks:
            await stack.enter_async_context(lock)
        yield


async def create_appointment(
    db: AsyncSession, principal: Principal, payload: AppointmentCreateRequest
) -> Appointment:
    """Create a new appointment after multi-tenant, range, and overlap validations."""
    start_utc = payload.start_time.astimezone(timezone.utc)
    end_utc = payload.end_time.astimezone(timezone.utc)

    # 1. Validate time range (RN-07: end_time must be strictly after start_time)
    if end_utc <= start_utc:
        raise InvalidTimeRange("end_time must be after start_time")

    # 2. Validate tenant-scoped references (D5 / Rule 1)
    # Patient check
    patient = await PatientRepository(db, principal).get(payload.patient_id)
    if patient is None:
        raise PatientNotFound()

    # Dentist check (must belong to clinic and have role 'dentist', D12)
    dentist = await UserRepository(db).get_in_clinic(
        principal.clinic_id, payload.dentist_id
    )
    if dentist is None or dentist.role != "dentist":
        raise DentistNotFound()

    # Box check
    box = await BoxRepository(db, principal).get(payload.box_id)
    if box is None:
        raise BoxNotFound()

    # 3. Check overlaps (RN-01) with concurrency protection
    repo = AppointmentRepository(db, principal)
    await repo.lock_resources(payload.dentist_id, payload.box_id)
    overlapping = await repo.find_overlapping(
        start_time=start_utc,
        end_time=end_utc,
        dentist_id=payload.dentist_id,
        box_id=payload.box_id,
    )
    if overlapping:
        raise AppointmentOverlap()

    # 4. Construct and persist
    appointment = Appointment(
        clinic_id=principal.clinic_id,
        patient_id=payload.patient_id,
        dentist_id=payload.dentist_id,
        box_id=payload.box_id,
        start_time=start_utc,
        end_time=end_utc,
        status="scheduled",
        notes=payload.notes,
    )
    return await repo.add(appointment)


async def get_appointment(
    db: AsyncSession, principal: Principal, appointment_id: uuid.UUID
) -> Appointment:
    """Retrieve an appointment by ID, strictly scoped to principal clinic."""
    appointment = await AppointmentRepository(db, principal).get(appointment_id)
    if appointment is None:
        raise AppointmentNotFound()
    return appointment


async def list_appointments(
    db: AsyncSession,
    principal: Principal,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    status: str | None = None,
) -> list[Appointment]:
    """List appointments for the authenticated clinic with optional range and status filters."""
    start_utc = (
        start_time.astimezone(timezone.utc)
        if start_time is not None and start_time.tzinfo is not None
        else (start_time.replace(tzinfo=timezone.utc) if start_time is not None else None)
    )
    end_utc = (
        end_time.astimezone(timezone.utc)
        if end_time is not None and end_time.tzinfo is not None
        else (end_time.replace(tzinfo=timezone.utc) if end_time is not None else None)
    )

    repo = AppointmentRepository(db, principal)
    appointments = await repo.list_appointments(
        start_time=start_utc, end_time=end_utc, status=status
    )
    return list(appointments)


async def update_appointment_status(
    db: AsyncSession,
    principal: Principal,
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdateRequest,
) -> Appointment:
    """Transition an appointment's status according to the transition matrix."""
    repo = AppointmentRepository(db, principal)
    appointment = await repo.get(appointment_id)
    if appointment is None:
        raise AppointmentNotFound()

    allowed = VALID_TRANSITIONS.get(appointment.status, set())
    if payload.status not in allowed:
        raise InvalidAppointmentTransition(
            f"Cannot transition appointment from '{appointment.status}' to '{payload.status}'"
        )

    appointment.status = payload.status
    return await repo.save(appointment)
