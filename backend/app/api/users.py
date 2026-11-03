"""Intra-clinic user administration router: `/api/v1/users` (admin only).

The guard ``require_roles("admin")`` denies receptionists and dentists before any
side effect (task 5.3) and the tenant scope always comes from the session.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services import users as users_service
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/users", tags=["users"])

AdminOnly = Depends(require_roles("admin"))


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    principal: Principal = AdminOnly,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a user assigned to the authenticated admin's clinic."""
    user = await users_service.create_user(db, principal, payload)
    await db.commit()
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    principal: Principal = AdminOnly,
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List the users of the authenticated admin's clinic only."""
    users = await users_service.list_users(db, principal)
    return [UserResponse.model_validate(user) for user in users]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    principal: Principal = AdminOnly,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update name, role and/or state of a user of the admin's clinic."""
    user = await users_service.update_user(db, principal, user_id, payload)
    await db.commit()
    return UserResponse.model_validate(user)
