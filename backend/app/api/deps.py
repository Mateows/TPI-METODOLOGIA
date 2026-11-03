"""FastAPI authentication/authorization dependencies (design D4/D5).

Routers depend on ``get_current_principal`` (or on ``require_roles(...)``) and
never read a ``clinic_id`` from the request to scope data.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.errors import AuthenticationError, AuthorizationError
from app.models.user import USER_ROLES
from app.services.principal import Principal, resolve_principal

# ``auto_error=False`` so a missing header yields our own 401 body (D10).
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    """Resolve the caller from ``Authorization: Bearer <access token>``."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("authentication required")
    return await resolve_principal(db, credentials.credentials)


PrincipalGuard = Callable[..., Awaitable[Principal]]


def get_clock() -> Callable[[], datetime]:
    """Injectable clock (design D11) so token lifetimes are testable."""
    return utcnow


def require_roles(*roles: str) -> PrincipalGuard:
    """Build a guard allowing only ``roles`` (deny by default, D5).

    Declaring an unknown role is a programming error and fails at import time.
    """
    unknown = set(roles) - set(USER_ROLES)
    if unknown:
        raise ValueError(f"unknown roles declared: {sorted(unknown)}")
    allowed = frozenset(roles)

    async def _guard(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed:
            raise AuthorizationError("role not permitted for this operation")
        return principal

    return _guard
