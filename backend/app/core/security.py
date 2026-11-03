"""Auth primitives: password hashing, access tokens and opaque refresh tokens.

Single wrapper around bcrypt and PyJWT (design D1) so unit tests never depend on
FastAPI. Every function that depends on time accepts an injectable clock
(design D11), which keeps expiry/rotation tests deterministic without sleeping.

Never log passwords, hashes or token values (Ley 25.326).
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.database import utcnow

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
BCRYPT_COST = 12
# 32 random bytes == 256 bits of entropy for the opaque refresh token (D3).
REFRESH_TOKEN_BYTES = 32


class TokenError(Exception):
    """Any access token that cannot be trusted (bad signature, shape or type)."""


class ExpiredTokenError(TokenError):
    """Token signature is valid but its ``exp`` claim is in the past."""


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash (cost 12) suitable for persistence."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)
    ).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check of a plain password against a stored hash.

    A malformed or empty stored hash fails closed instead of raising: corrupted
    rows must never surface as a 500 or leak driver details (design D10).
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    clinic_id: str,
    role: str,
    expires_delta: timedelta | None = None,
    now: Callable[[], datetime] = utcnow,
) -> str:
    """Sign a short-lived HS256 access token with the minimal claim set (D2)."""
    issued_at = now()
    lifetime = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "clinic_id": clinic_id,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "jti": secrets.token_urlsafe(16),
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + lifetime).timestamp()),
    }
    return jwt.encode(
        payload, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM
    )


def decode_access_token(
    token: str, *, now: Callable[[], datetime] = utcnow
) -> dict[str, Any]:
    """Verify signature/shape/type/expiry and return the token claims.

    Expiry is compared against the injected clock instead of PyJWT's internal
    wall clock so tests can move time forward deterministically (D11).
    """
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except jwt.InvalidTokenError as exc:  # bad signature, malformed, etc.
        raise TokenError("invalid access token") from exc

    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("unexpected token type")

    expires_at = claims.get("exp")
    if not isinstance(expires_at, (int, float)):
        raise TokenError("missing exp claim")

    if datetime.fromtimestamp(expires_at, tz=UTC) <= now():
        raise ExpiredTokenError("access token expired")

    return claims


def generate_refresh_token() -> str:
    """Return a fresh 256-bit opaque refresh value (never persisted as-is)."""
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 hex digest stored in ``refresh_tokens.token_hash``."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
