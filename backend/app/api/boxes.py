"""Clinic-scoped boxes router: `/api/v1/boxes`.

Creation is admin-only (administrative resource, like `/users`); every
authenticated role may list and read. The tenant scope comes from the session.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal
from app.core.database import get_db
from app.schemas.boxes import BoxCreateRequest, BoxResponse
from app.services import boxes as boxes_service
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/boxes", tags=["boxes"])

Authenticated = Depends(get_current_principal)


@router.post("", response_model=BoxResponse, status_code=201)
async def create_box(
    payload: BoxCreateRequest,
    principal: Principal = Authenticated,
    db: AsyncSession = Depends(get_db),
) -> BoxResponse:
    """Create a box assigned to the authenticated caller's clinic."""
    box = await boxes_service.create_box(db, principal, payload)
    await db.commit()
    return BoxResponse.model_validate(box)


@router.get("", response_model=list[BoxResponse])
async def list_boxes(
    principal: Principal = Authenticated,
    db: AsyncSession = Depends(get_db),
) -> list[BoxResponse]:
    """List boxes belonging to the authenticated caller's clinic."""
    boxes = await boxes_service.list_boxes(db, principal)
    return [BoxResponse.model_validate(box) for box in boxes]
