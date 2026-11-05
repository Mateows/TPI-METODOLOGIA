"""``Patient`` persistence scoped by ``principal.clinic_id`` (design D3/D5/D13)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction

from app.models.patient import Patient
from app.repositories.base import ClinicScope, TenantScopedRepository


@asynccontextmanager
async def _isolated_savepoint(db: AsyncSession) -> AsyncIterator[AsyncSessionTransaction]:
    """Open a savepoint without triggering SQLAlchemy's pre-snapshot flush.

    By default, ``Session.begin_nested()`` flushes all pending dirty objects
    before emitting ``SAVEPOINT``. When ``save()`` is called on an already-mutated
    instance whose changes violate a constraint (e.g. duplicate DNI), that
    pre-snapshot flush fails on the parent transaction instead of inside the
    savepoint, deassociating the root transaction. Suppressing ``_flushing`` during
    savepoint entry ensures ``SAVEPOINT`` is established first so the subsequent
    flush runs safely within it.
    """
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


class PatientRepository(TenantScopedRepository[Patient]):
    """Tenant-scoped repository for ``Patient`` records."""

    def __init__(self, db: AsyncSession, principal: ClinicScope) -> None:
        super().__init__(Patient, db, principal)

    async def get_by_dni(self, dni: str) -> Patient | None:
        """Return the patient matching ``dni`` inside the caller's clinic, or ``None``."""
        result = await self.db.execute(self.scoped(Patient.dni == dni))
        return result.scalar_one_or_none()

    async def dni_exists(
        self, dni: str, exclude_id: uuid.UUID | None = None
    ) -> bool:
        """Check whether ``dni`` is already registered in the caller's clinic."""
        criteria = [Patient.dni == dni]
        if exclude_id is not None:
            criteria.append(Patient.id != exclude_id)
        result = await self.db.execute(self.scoped(*criteria))
        return result.scalars().first() is not None

    async def search(
        self,
        q: str | None = None,
        *,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Patient]:
        """List or search patients of the caller's clinic ordered by last/first name."""
        criteria = []
        if not include_inactive:
            criteria.append(Patient.is_active.is_(True))
        if q is not None and q.strip():
            term = f"%{q.strip()}%"
            criteria.append(
                or_(
                    Patient.dni.ilike(term),
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                )
            )
        statement = (
            self.scoped(*criteria)
            .order_by(Patient.last_name.asc(), Patient.first_name.asc(), Patient.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(statement)
        return result.scalars().all()

    async def add(self, patient: Patient) -> Patient:
        """Insert ``patient`` inside a savepoint and flush (D3)."""
        async with _isolated_savepoint(self.db):
            self.db.add(patient)
            await self.db.flush()
        return patient

    async def save(self, patient: Patient) -> Patient:
        """Flush updates to ``patient`` inside a savepoint (D3)."""
        async with _isolated_savepoint(self.db):
            self.db.add(patient)
            await self.db.flush()
        return patient
