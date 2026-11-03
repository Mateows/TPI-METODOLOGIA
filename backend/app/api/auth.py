"""Authentication router: `/api/v1/auth` (design D2/D3/D4).

Thin HTTP layer: validation lives in the Pydantic schemas, rules in
``app.services.auth``. No session logic is duplicated here.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_current_principal
from app.core.database import get_db
from app.schemas.auth import (
    ClinicSummary,
    LoginRequest,
    MeResponse,
    PasswordChangeRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services import auth as auth_service
from app.services.auth import IssuedSession
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _token_response(session: IssuedSession) -> TokenResponse:
    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        role=session.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> TokenResponse:
    """Authenticate by email + password and open a session."""
    session = await auth_service.authenticate(
        db, payload.email, payload.password, now=clock
    )
    await db.commit()
    return _token_response(session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token."""
    session = await auth_service.refresh_session(
        db, payload.refresh_token, now=clock
    )
    await db.commit()
    return _token_response(session)


@router.post("/logout", status_code=204, response_model=None)
async def logout(
    payload: RefreshRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> None:
    """Revoke the caller's refresh session; always an empty 204 on success."""
    await auth_service.logout(db, principal, payload.refresh_token, now=clock)


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Principal = Depends(get_current_principal),
) -> MeResponse:
    """Return only the authenticated user's own identity and clinic."""
    return MeResponse(
        id=principal.user.id,
        email=principal.user.email,
        full_name=principal.user.full_name,
        role=principal.role,
        is_active=principal.user.is_active,
        clinic=ClinicSummary.model_validate(principal.clinic),
    )


@router.patch("/password", status_code=204, response_model=None)
async def change_password(
    payload: PasswordChangeRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> None:
    """Self-service password change; revokes the user's refresh sessions."""
    await auth_service.change_password(
        db,
        principal,
        payload.current_password,
        payload.new_password,
        now=clock,
    )
