"""``Appointment`` persistence (design D1/D3/D5/D13).

Persistence Invariants:
1. Multi-Tenant Isolation (Rule 1, D5):
   Every read, query, and write is strictly scoped by ``principal.clinic_id`` via
   ``TenantScopedRepository[Appointment]``. A record belonging to another clinic
   is returned as ``None``, indistinguishable from an absent id (HTTP 404).

2. UTC Datetime Storage (RN-07, D5):
   All persisted datetimes (``start_time``, ``end_time``) must be timezone-aware
   and normalized to UTC before persisting. Naive datetimes are rejected at the
   validation layer and never reach persistence.

3. Overlap Prevention (RN-01, D1):
   Overlap is evaluated within the authenticated clinic for non-cancelled
   appointments sharing either ``dentist_id`` or ``box_id`` using the open
   interval condition:
       existing.start_time < new.end_time AND existing.end_time > new.start_time
   Appointments in status ``cancelled`` are excluded from overlap checks.
   Contiguous appointments (where existing.end_time == new.start_time) are
   strictly permitted.

4. Concurrency & Integrity (D2, RN-01):
   Mutations are executed within isolated savepoints to ensure atomicity.
   Resource locking (``with_for_update``) on the dentist and box serializes
   concurrent bookings, while PostgreSQL ``EXCLUDE USING gist`` acts as a
   database-level safety net; any constraint violation is mapped to
   ``AppointmentOverlap``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction

from app.core.errors import AppointmentOverlap
from app.models.appointment import Appointment
from app.models.box import Box
from app.models.user import User
from app.repositories.base import ClinicScope, TenantScopedRepository


@asynccontextmanager
async def _isolated_savepoint(db: AsyncSession) -> AsyncIterator[AsyncSessionTransaction]:
    """Open a savepoint without triggering SQLAlchemy's pre-snapshot flush."""
    sp_cm = db.begin_nested()
    db.sync_session._flushing = True
    try:
        sp = await sp_cm.__aenter__()
    finally:
        db.sync_session._flushing = False
    try:
        yield sp
    except BaseException as exc:
        if not await sp_cm.__aexit__(type(exc), exc, exc.__traceback__):
            raise
    else:
        await sp_cm.__aexit__(None, None, None)


class AppointmentRepository(TenantScopedRepository[Appointment]):
    """Clinic-scoped persistence for ``Appointment``."""

    def __init__(self, db: AsyncSession, principal: ClinicScope) -> None:
        super().__init__(Appointment, db, principal)

    async def lock_resources(self, dentist_id: uuid.UUID, box_id: uuid.UUID) -> None:
        """Acquire row-level locks on the target dentist and box.

        Serializes concurrent appointment creations for the same dentist or box,
        guaranteeing serialized overlap evaluations.
        """
        await self.db.execute(
            select(User.id)
            .where(User.clinic_id == self.principal.clinic_id, User.id == dentist_id)
            .with_for_update()
        )
        await self.db.execute(
            select(Box.id)
            .where(Box.clinic_id == self.principal.clinic_id, Box.id == box_id)
            .with_for_update()
        )

    async def add(self, appointment: Appointment) -> Appointment:
        """Insert ``appointment`` inside a savepoint and flush (the caller commits)."""
        try:
            async with _isolated_savepoint(self.db):
                self.db.add(appointment)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppointmentOverlap() from exc
        return appointment

    async def save(self, appointment: Appointment) -> Appointment:
        """Update an existing appointment within a savepoint and flush."""
        try:
            async with _isolated_savepoint(self.db):
                self.db.add(appointment)
                await self.db.flush()
        except IntegrityError as exc:
            raise AppointmentOverlap() from exc
        return appointment

    async def find_overlapping(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        dentist_id: uuid.UUID,
        box_id: uuid.UUID,
        exclude_appointment_id: uuid.UUID | None = None,
    ) -> Sequence[Appointment]:
        """Find non-cancelled appointments in the same clinic overlapping [start_time, end_time)."""
        criteria = [
            Appointment.status != "cancelled",
            or_(
                Appointment.dentist_id == dentist_id,
                Appointment.box_id == box_id,
            ),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        ]
        if exclude_appointment_id is not None:
            criteria.append(Appointment.id != exclude_appointment_id)

        stmt = self.scoped(*criteria)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_appointments(
        self,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
    ) -> Sequence[Appointment]:
        """List appointments for the authenticated clinic with optional date range and status filters."""
        criteria = []
        if start_time is not None:
            criteria.append(Appointment.start_time >= start_time)
        if end_time is not None:
            criteria.append(Appointment.start_time <= end_time)
        if status is not None:
            criteria.append(Appointment.status == status)

        stmt = self.scoped(*criteria).order_by(Appointment.start_time.asc())
        result = await self.db.execute(stmt)
        return result.scalars().all()
