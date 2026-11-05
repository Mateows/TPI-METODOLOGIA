"""``Clinic`` persistence (design D7/D8/D13).

Lookups here are global by nature: they serve operator bootstrap (idempotency
by ``tax_id``, unique public ``slug``), never a tenant-scoped request.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic


class ClinicRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_tax_id(self, tax_id: str) -> Clinic | None:
        return (
            await self.db.execute(select(Clinic).where(Clinic.tax_id == tax_id))
        ).scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        return bool(await self.db.scalar(select(Clinic.id).where(Clinic.slug == slug)))

    async def add(self, clinic: Clinic) -> Clinic:
        self.db.add(clinic)
        await self.db.flush()
        return clinic
