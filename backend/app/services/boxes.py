"""Box administration (design D5/D13).

The clinic of a box is derived only from ``principal.clinic_id``; persistence is
delegated to ``BoxRepository``. The service only flushes: the router commits.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BoxNotFound
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


async def get_box(
    db: AsyncSession, principal: Principal, box_id: uuid.UUID
) -> Box:
    """Retrieve a box by ID, strictly scoped to the caller's clinic (404 on foreign/absent)."""
    box = await BoxRepository(db, principal).get(box_id)
    if box is None:
        raise BoxNotFound()
    return box


async def list_boxes(db: AsyncSession, principal: Principal) -> list[Box]:
    """List only boxes belonging to the caller's clinic."""
    return list(await BoxRepository(db, principal).list())
