"""``Box`` persistence (design D5/D13).

Every read is clinic-scoped through ``TenantScopedRepository``: a box of another
clinic is returned as ``None``, exactly like an absent id.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.box import Box
from app.repositories.base import ClinicScope, TenantScopedRepository


class BoxRepository(TenantScopedRepository[Box]):
    """Clinic-scoped reads/writes for ``Box``."""

    def __init__(self, db: AsyncSession, principal: ClinicScope) -> None:
        super().__init__(Box, db, principal)

    async def add(self, box: Box) -> Box:
        """Insert ``box`` inside a savepoint and flush (the caller commits)."""
        async with self.db.begin_nested():
            self.db.add(box)
            await self.db.flush()
        return box
