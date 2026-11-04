"""Box administration (design D5/D13).

The clinic of a box is derived only from ``principal.clinic_id``; persistence is
delegated to ``BoxRepository``. The service only flushes: the router commits.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.box import Box
from app.repositories.boxes import BoxRepository
from app.schemas.boxes import BoxCreateRequest
from app.services.principal import Principal


async def create_box(
    db: AsyncSession, principal: Principal, payload: BoxCreateRequest
) -> Box:
    """Create a box inside the caller's clinic (never a client-supplied one)."""
    box = Box(
        clinic_id=principal.clinic_id,
        name=payload.name,
        status="active",
    )
    return await BoxRepository(db, principal).add(box)
