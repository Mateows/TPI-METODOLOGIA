"""Authentication business logic (design D2/D3/D4).

Routers stay thin: this module owns credential verification, token issuance and
the refresh session lifecycle. It never logs credentials or token values.

Operational logging (spec "No credential leakage in operational logs") is
deliberately minimal: an event name, a result and — when an identity is already
proven — the opaque ``user_id``. Never the email, the full name, the plain
password, the stored hash or any token value (Ley 25.326).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    InvalidCredentials,
    SessionRevoked,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.clinic import Clinic
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.principal import Principal


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """Tokens handed to the client; the refresh value is never persisted raw."""

    access_token: str
    refresh_token: str
    role: str


logger = logging.getLogger("app.auth")

# Fixed messages per event: the outcome only ever travels as structured ``extra``
# fields, never as free text, so no credential or identity can slip into it.
_LOGIN_FAILED = "auth.login rejected"
_LOGIN_SUCCEEDED = "auth.login succeeded"
_REFRESH_FAILED = "auth.refresh rejected"
_REFRESH_SUCCEEDED = "auth.refresh succeeded"


def _log(
    event: str,
    message: str,
    *,
    result: str,
    user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    """Emit one structured auth event (INFO on success, WARNING on rejection).

    ``user_id`` is an opaque internal key for correlation; ``reason`` is a fixed
    tag. Neither carries email, full name, passwords, hashes, tokens or clinical
    content (Ley 25.326).
    """
    extra: dict[str, str] = {"event": event, "result": result}
    if reason is not None:
        extra["reason"] = reason
    if user_id is not None:
        extra["user_id"] = str(user_id)
    level = logging.INFO if result == "success" else logging.WARNING
    logger.log(level, message, extra=extra)


def _log_login_failure() -> None:
    """Login failures share one fixed shape, whatever the underlying cause.

    Distinguishing "unknown email" from "wrong password" — even by a reason
    field or a user id — would rebuild server-side the 401 the API hides.
    """
    _log("auth.login", _LOGIN_FAILED, result="failure")


def _log_login_success(user_id: uuid.UUID) -> None:
    _log("auth.login", _LOGIN_SUCCEEDED, result="success", user_id=user_id)


def _log_refresh(
    result: str,
    *,
    user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> None:
    _log(
        "auth.refresh",
        _REFRESH_SUCCEEDED if result == "success" else _REFRESH_FAILED,
        result=result,
        user_id=user_id,
        reason=reason,
    )


# Design D3 / Risks: a rotated token presented again within this window is a
# benign concurrent retry (two tabs) — it is still rejected, but the family is
# not revoked. Beyond it, the token is treated as stolen and the family dies.
REFRESH_REPLAY_GRACE = timedelta(seconds=10)


def _as_utc(value: datetime) -> datetime:
    """SQLite drops the offset; treat naive timestamps as UTC (design D9)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _access_token_for(user: User, now: Callable[[], datetime]) -> str:
    return create_access_token(
        subject=str(user.id),
        clinic_id=str(user.clinic_id),
        role=user.role,
        now=now,
    )


async def _persist_refresh(
    db: AsyncSession,
    user: User,
    family_id: uuid.UUID,
    now: Callable[[], datetime],
) -> tuple[str, RefreshToken]:
    """Create a new refresh row for ``user`` and return its raw value + record."""
    raw = generate_refresh_token()
    issued_at = now()
    row = RefreshToken(
        user_id=user.id,
        clinic_id=user.clinic_id,
        family_id=family_id,
        token_hash=hash_refresh_token(raw),
        issued_at=issued_at,
        expires_at=issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(row)
    await db.flush()
    return raw, row


async def authenticate(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    now: Callable[[], datetime] = utcnow,
) -> IssuedSession:
    """Verify credentials and open a new session family.

    Unknown email, wrong password and a deactivated account all answer with the
    same generic 401 so nothing is disclosed (spec "Invalid credentials reveal
    nothing"). A closed tenant answers 403 because the identity is authentic.
    """
    row = (
        await db.execute(
            select(User, Clinic)
            .join(Clinic, User.clinic_id == Clinic.id)
            .where(User.email == email.strip().lower())
        )
    ).first()
    if row is None:
        _log_login_failure()
        raise InvalidCredentials()

    user, clinic = row
    if not verify_password(password, user.password_hash):
        _log_login_failure()
        raise InvalidCredentials()
    if not user.is_active:
        _log_login_failure()
        raise InvalidCredentials()
    if not clinic.is_active:
        # The identity is authentic here, so the API answers 403 and the log may
        # name the (opaque) user id without revealing anything the response does
        # not already tell this caller.
        _log(
            "auth.login",
            _LOGIN_FAILED,
            result="failure",
            reason="inactive_clinic",
            user_id=user.id,
        )
        raise AuthorizationError("clinic is not active")

    raw_refresh, _row = await _persist_refresh(db, user, uuid.uuid4(), now)
    _log_login_success(user.id)
    return IssuedSession(
        access_token=_access_token_for(user, now),
        refresh_token=raw_refresh,
        role=user.role,
    )


async def _load_session_account(
    db: AsyncSession, raw_refresh: str
) -> tuple[RefreshToken, User, Clinic]:
    """Load the refresh row with its user and clinic, or fail with 401."""
    row = (
        await db.execute(
            select(RefreshToken, User, Clinic)
            .join(User, RefreshToken.user_id == User.id)
            .join(Clinic, User.clinic_id == Clinic.id)
            .where(RefreshToken.token_hash == hash_refresh_token(raw_refresh))
        )
    ).first()
    if row is None:
        raise SessionRevoked()
    token_row, user, clinic = row
    # Defensive: a refresh row must never scope a user to a foreign clinic.
    if token_row.clinic_id != user.clinic_id:
        raise SessionRevoked()
    return token_row, user, clinic


async def _revoke_family(
    db: AsyncSession, family_id: uuid.UUID, revoked_at: datetime
) -> None:
    rows = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    for row in rows:
        row.revoked_at = revoked_at
    await db.flush()


async def refresh_session(
    db: AsyncSession,
    raw_refresh: str,
    *,
    now: Callable[[], datetime] = utcnow,
) -> IssuedSession:
    """Rotate a valid refresh token, detecting reuse of a spent one.

    A spent token inside the grace window is rejected without revoking the
    family (concurrent tabs, design Risks); outside it, the whole family is
    revoked as a compromised session (spec "Reused refresh token revokes the
    session").
    """
    try:
        token_row, user, clinic = await _load_session_account(db, raw_refresh)
    except SessionRevoked:
        # Unknown or cross-clinic token: the value is never logged.
        _log_refresh("failure", reason="unknown")
        raise

    if token_row.revoked_at is not None:
        _log_refresh("failure", user_id=user.id, reason="revoked")
        raise SessionRevoked()
    if not user.is_active:
        _log_refresh("failure", user_id=user.id, reason="inactive_user")
        raise AuthenticationError("account is not active")
    if not clinic.is_active:
        _log_refresh("failure", user_id=user.id, reason="inactive_clinic")
        raise AuthorizationError("clinic is not active")

    current = now()
    if _as_utc(token_row.expires_at) <= current:
        token_row.revoked_at = current
        await db.commit()
        _log_refresh("failure", user_id=user.id, reason="expired")
        raise SessionRevoked()

    if token_row.rotated_at is not None:
        spent_for = current - _as_utc(token_row.rotated_at)
        if spent_for > REFRESH_REPLAY_GRACE:
            # Reuse outside the grace window: treat the family as compromised.
            # The revocation must survive the error response, so commit here.
            await _revoke_family(db, token_row.family_id, current)
            await db.commit()
            _log_refresh("failure", user_id=user.id, reason="reuse")
            raise SessionRevoked()
        # Benign duplicate request (concurrent tabs): refuse the spent value
        # without killing the legitimate successor.
        _log_refresh("failure", user_id=user.id, reason="already_rotated")
        raise SessionRevoked("refresh token already rotated")

    raw_new, new_row = await _persist_refresh(db, user, token_row.family_id, now)
    token_row.rotated_at = current
    token_row.replaced_by_id = new_row.id
    await db.flush()

    _log_refresh("success", user_id=user.id)
    return IssuedSession(
        access_token=_access_token_for(user, now),
        refresh_token=raw_new,
        role=user.role,
    )


async def logout(
    db: AsyncSession,
    principal: Principal,
    raw_refresh: str,
    *,
    now: Callable[[], datetime] = utcnow,
) -> None:
    """Revoke the caller's refresh session (spec Logout revokes the session).

    A refresh value that is unknown or belongs to another user is answered
    generically and never revoked, so the endpoint cannot be used as a
    cross-user denial of service.
    """
    token_row, user, _clinic = await _load_session_account(db, raw_refresh)
    if user.id != principal.user_id or token_row.clinic_id != principal.clinic_id:
        raise SessionRevoked("session is no longer valid")
    await _revoke_family(db, token_row.family_id, now())
    await db.commit()


async def change_password(
    db: AsyncSession,
    principal: Principal,
    current_password: str,
    new_password: str,
    *,
    now: Callable[[], datetime] = utcnow,
) -> None:
    """Replace the caller's password and revoke every refresh session.

    The endpoint does not receive a refresh token, so the caller's own session
    cannot be identified; revoking all of the user's sessions is the safe
    superset of the spec ("revokes that user's other sessions"). The caller's
    access token stays valid until it expires (stateless JWT).
    """
    user = await db.get(User, principal.user_id)
    if user is None or not verify_password(current_password, user.password_hash):
        raise InvalidCredentials("current password does not match")

    user.password_hash = hash_password(new_password)
    revoked_at = now()
    rows = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    for row in rows:
        row.revoked_at = revoked_at
    await db.commit()
