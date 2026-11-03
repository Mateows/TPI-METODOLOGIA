"""Task 1.2 — security primitives: password hashing + JWT + opaque refresh.

Unit level only (no FastAPI): the wrapper in app/core/security.py is the single
place that knows about bcrypt and PyJWT (design D1). Expiry is exercised with
an injected clock (design D11) so nothing sleeps and freezegun is not needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    ExpiredTokenError,
    TokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

FIXED_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _fixed_now() -> datetime:
    return FIXED_NOW


def test_hash_password_is_salted_bcrypt_cost_12_and_verifiable():
    """WHEN hashing the same password twice THEN hashes differ (salt) and verify."""
    first = hash_password("Secreta-123")
    second = hash_password("Secreta-123")

    assert first != second
    assert "Secreta-123" not in first
    assert first.startswith("$2b$12$")
    assert verify_password("Secreta-123", first) is True
    assert verify_password("Secreta-123", second) is True
    assert verify_password("otra-clave", first) is False


def test_verify_password_returns_false_for_malformed_hash():
    """A corrupted stored hash must not raise; it fails closed."""
    assert verify_password("Secreta-123", "not-a-bcrypt-hash") is False
    assert verify_password("Secreta-123", "") is False


def test_access_token_round_trip_carries_minimal_claims():
    """WHEN signing THEN decode returns sub/clinic_id/role/type/jti/iat/exp."""
    token = create_access_token(
        subject="user-1",
        clinic_id="clinic-1",
        role="admin",
        now=_fixed_now,
    )
    claims = decode_access_token(token, now=_fixed_now)

    assert claims["type"] == ACCESS_TOKEN_TYPE == "access"
    assert claims["sub"] == "user-1"
    assert claims["clinic_id"] == "clinic-1"
    assert claims["role"] == "admin"
    assert isinstance(claims["jti"], str) and claims["jti"]
    assert claims["iat"] == int(FIXED_NOW.timestamp())
    assert claims["exp"] - claims["iat"] == 15 * 60


def test_access_token_jti_is_unique_per_issue():
    """Two tokens for the same principal must be individually identifiable."""
    first = create_access_token(subject="u", clinic_id="c", role="dentist", now=_fixed_now)
    second = create_access_token(subject="u", clinic_id="c", role="dentist", now=_fixed_now)

    assert decode_access_token(first, now=_fixed_now)["jti"] != decode_access_token(
        second, now=_fixed_now
    )["jti"]


def test_expired_token_is_rejected_using_injected_clock():
    """WHEN the injected clock passes exp THEN ExpiredTokenError, no data read."""
    token = create_access_token(subject="u", clinic_id="c", role="admin", now=_fixed_now)

    later = FIXED_NOW + timedelta(minutes=15, seconds=1)
    with pytest.raises(ExpiredTokenError):
        decode_access_token(token, now=lambda: later)


def test_token_is_valid_at_exp_boundary_minus_one_second():
    """Triangulation: just before exp the token still decodes."""
    token = create_access_token(subject="u", clinic_id="c", role="admin", now=_fixed_now)

    almost = FIXED_NOW + timedelta(minutes=14, seconds=59)
    assert decode_access_token(token, now=lambda: almost)["sub"] == "u"


def test_tampered_token_is_rejected():
    """WHEN any byte of the signed token changes THEN the signature fails."""
    token = create_access_token(subject="u", clinic_id="c", role="admin", now=_fixed_now)
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-1]}{'A' if signature[-1] != 'A' else 'B'}"

    with pytest.raises(TokenError):
        decode_access_token(tampered, now=_fixed_now)


def test_token_signed_with_foreign_secret_is_rejected():
    """A well-formed token signed by another key must never be accepted."""
    foreign = jwt.encode(
        {
            "sub": "u",
            "clinic_id": "c",
            "role": "admin",
            "type": "access",
            "jti": "foreign",
            "iat": int(FIXED_NOW.timestamp()),
            "exp": int((FIXED_NOW + timedelta(minutes=15)).timestamp()),
        },
        "a-different-secret",
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(foreign, now=_fixed_now)


def test_token_of_wrong_type_is_rejected():
    """A refresh-like payload cannot be used as an access token."""
    wrong_type = jwt.encode(
        {
            "sub": "u",
            "clinic_id": "c",
            "role": "admin",
            "type": "refresh",
            "jti": "x",
            "iat": int(FIXED_NOW.timestamp()),
            "exp": int((FIXED_NOW + timedelta(minutes=15)).timestamp()),
        },
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        decode_access_token(wrong_type, now=_fixed_now)


def test_refresh_token_is_opaque_256_bits_and_hashed_with_sha256():
    """Refresh values are random, URL-safe and only their SHA-256 is stored."""
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert len(first) >= 43  # 256 bits base64url without padding
    digest = hash_refresh_token(first)
    assert len(digest) == 64
    assert digest == hash_refresh_token(first)
    assert digest != hash_refresh_token(second)
    assert first not in digest
