"""Clinic-scoped boxes router: `/api/v1/boxes`.

Creation is admin-only (administrative resource, like `/users`); every
authenticated role may list and read. The tenant scope comes from the session.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal, require_roles
from app.core.database import get_db
from app.schemas.boxes import BoxCreateRequest, BoxResponse
from app.services import boxes as boxes_service
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/boxes", tags=["boxes"])

Authenticated = Depends(get_current_principal)
AdminOnly = Depends(require_roles("admin"))


@router.post("", response_model=BoxResponse, status_code=201)
async def create_box(
    payload: BoxCreateRequest,
    principal: Principal = AdminOnly,
    db: AsyncSession = Depends(get_db),
) -> BoxResponse:
    """Create a box assigned to the authenticated admin's clinic.

    Administrative operation restricted to clinic administrators (AdminOnly);
    receptionists and dentists receive 403 Forbidden without database side effects.
    """
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


@router.get("/{box_id}", response_model=BoxResponse)
async def get_box(
    box_id: uuid.UUID,
    principal: Principal = Authenticated,
    db: AsyncSession = Depends(get_db),
) -> BoxResponse:
    """Retrieve an individual box by ID belonging to the authenticated caller's clinic."""
    box = await boxes_service.get_box(db, principal, box_id)
    return BoxResponse.model_validate(box)
