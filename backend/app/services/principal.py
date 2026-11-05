"""Per-request identity: the single source of the active tenant (design D4/D5).

The access token is only an *indication* of identity: ``resolve_principal``
reloads ``User`` + ``Clinic`` from the database on every request, so role
changes and account deactivations apply immediately.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import TokenError, decode_access_token
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.users import UserRepository


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated caller bound to exactly one clinic (RN-02).

    ``user``/``clinic`` are the freshly loaded rows; ``clinic_id`` is the only
    tenant scope a service may use — never a client-supplied value.
    """

    user_id: uuid.UUID
    clinic_id: uuid.UUID
    role: str
    user: User
    clinic: Clinic


def _as_uuid(value: object) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("invalid access token") from exc


async def resolve_principal(
    db: AsyncSession,
    token: str,
    *,
    now: Callable[[], datetime] = utcnow,
) -> Principal:
    """Decode ``token`` and return the current, active principal.

    401 when the token is unusable, the user is unknown/inactive or the token is
    stale; 403 when the clinic is inactive (authentic session, closed tenant).
    """
    try:
        claims = decode_access_token(token, now=now)
    except TokenError as exc:
        raise AuthenticationError("invalid or expired access token") from exc

    user_id = _as_uuid(claims.get("sub"))
    token_clinic_id = _as_uuid(claims.get("clinic_id"))

    row = await UserRepository(db).get_with_clinic_by_id(user_id)
    if row is None:
        raise AuthenticationError("unknown account")

    user, clinic = row
    if not user.is_active:
        raise AuthenticationError("account is not active")
    # A token issued before the user moved clinics must not keep the old scope.
    if token_clinic_id != user.clinic_id:
        raise AuthenticationError("stale session")
    if not clinic.is_active:
        raise AuthorizationError("clinic is not active")

    return Principal(
        user_id=user.id,
        clinic_id=clinic.id,
        role=user.role,
        user=user,
        clinic=clinic,
    )
