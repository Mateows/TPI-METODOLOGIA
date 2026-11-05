"""Tasks 4.1–4.4 — authentication endpoints over the isolated test database.

Contract: ``{detail, code}`` on every failure, no credential material in any
response, and the active clinic always comes from the verified session.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api.deps import get_clock
from app.core.security import decode_access_token, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.services.auth import REFRESH_REPLAY_GRACE

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
PASSWORD = "/api/v1/auth/password"


class FakeClock:
    """Deterministic clock so grace/expiry are tested without sleeping (D11)."""

    def __init__(self) -> None:
        self.now = datetime.now(UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


@pytest.fixture()
def fake_clock(client):
    from app.main import app

    clock = FakeClock()
    app.dependency_overrides[get_clock] = lambda: clock
    return clock


async def test_login_with_valid_credentials_issues_a_session(client, seed_tenant):
    tenant = await seed_tenant(role="admin", email="admin@example.com")

    response = await client.post(
        LOGIN, json={"email": "admin@example.com", "password": "Secreta-123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type", "role"}
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert body["refresh_token"]

    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == str(tenant.user.id)
    assert claims["clinic_id"] == str(tenant.clinic.id)
    assert claims["role"] == "admin"

    # Password storage requirement: no plain password or hash in the response.
    assert "Secreta-123" not in response.text
    assert tenant.user.password_hash not in response.text


async def test_login_persists_only_the_refresh_hash(client, seed_tenant, test_session):
    await seed_tenant(email="hash@example.com")

    response = await client.post(
        LOGIN, json={"email": "hash@example.com", "password": "Secreta-123"}
    )
    raw = response.json()["refresh_token"]
    stored = (await test_session.execute(select(RefreshToken))).scalars().all()

    assert len(stored) == 1
    assert stored[0].token_hash == hash_refresh_token(raw)
    assert stored[0].token_hash != raw
    assert raw not in response.request.content.decode()


async def test_email_is_case_insensitive_at_login(client, seed_tenant):
    await seed_tenant(email="persona@example.com")

    response = await client.post(
        LOGIN, json={"email": "  PERSONA@Example.com ", "password": "Secreta-123"}
    )

    assert response.status_code == 200


async def test_wrong_password_and_unknown_email_are_indistinguishable(
    client, seed_tenant
):
    await seed_tenant(email="conocido@example.com")

    wrong = await client.post(
        LOGIN, json={"email": "conocido@example.com", "password": "otra-clave"}
    )
    unknown = await client.post(
        LOGIN, json={"email": "desconocido@example.com", "password": "otra-clave"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["code"] == "invalid_credentials"
    assert "access_token" not in wrong.json()
    assert "access_token" not in unknown.json()


async def test_inactive_user_cannot_log_in(client, seed_tenant):
    """Spec scenario: deactivated user gets the generic auth error, no token."""
    await seed_tenant(email="baja@example.com", user_active=False)

    response = await client.post(
        LOGIN, json={"email": "baja@example.com", "password": "Secreta-123"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert "access_token" not in response.json()


async def test_inactive_clinic_cannot_log_in(client, seed_tenant):
    """A valid account of a closed tenant gets an authorization error (D4)."""
    await seed_tenant(email="cerrada@example.com", clinic_active=False)

    response = await client.post(
        LOGIN, json={"email": "cerrada@example.com", "password": "Secreta-123"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def _auth_records(caplog) -> list[logging.LogRecord]:
    """Only the application auth logger's records (not httpx/SQLAlchemy noise)."""
    return [record for record in caplog.records if record.name == "app.auth"]


def _record_shape(record: logging.LogRecord) -> tuple:
    return (
        record.name,
        record.levelname,
        record.getMessage(),
        getattr(record, "event", None),
        getattr(record, "result", None),
        getattr(record, "reason", None),
        getattr(record, "user_id", None),
    )


async def test_login_attempts_never_leak_credentials_into_logs(
    client, seed_tenant, caplog
):
    """Spec "No credential leakage in operational logs" (RN-02, Ley 25.326).

    Both outcomes must be *recorded* (the positive half of the requirement) and
    whatever is recorded must never contain the plain password, the stored hash,
    the email or a token value.
    """
    tenant = await seed_tenant(email="logs@example.com")

    with caplog.at_level(logging.INFO, logger="app.auth"):
        failed = await client.post(
            LOGIN, json={"email": "logs@example.com", "password": "Incorrecta-999"}
        )
        success = await client.post(
            LOGIN, json={"email": "logs@example.com", "password": "Secreta-123"}
        )

    assert failed.status_code == 401
    assert success.status_code == 200

    records = _auth_records(caplog)
    outcomes = [(getattr(r, "event", None), getattr(r, "result", None)) for r in records]
    assert ("auth.login", "failure") in outcomes
    assert ("auth.login", "success") in outcomes

    logged = caplog.text
    assert "Incorrecta-999" not in logged
    assert "Secreta-123" not in logged
    assert tenant.user.password_hash not in logged
    assert success.json()["access_token"] not in logged
    assert success.json()["refresh_token"] not in logged
    assert "logs@example.com" not in "\n".join(r.getMessage() for r in records)


async def test_login_failure_log_cannot_distinguish_unknown_email_from_wrong_password(
    client, seed_tenant, caplog
):
    """Triangulation: both failures produce the same log entry.

    Logging a reason or a user id on only one of the two paths would rebuild,
    server-side, the distinction the API deliberately hides.
    """
    tenant = await seed_tenant(email="conocido@example.com")

    with caplog.at_level(logging.INFO, logger="app.auth"):
        wrong = await client.post(
            LOGIN, json={"email": "conocido@example.com", "password": "otra-clave"}
        )
        wrong_records = _auth_records(caplog)
        caplog.clear()
        unknown = await client.post(
            LOGIN, json={"email": "desconocido@example.com", "password": "otra-clave"}
        )
        unknown_records = _auth_records(caplog)

    assert wrong.status_code == unknown.status_code == 401
    assert len(wrong_records) == len(unknown_records) == 1
    assert _record_shape(wrong_records[0]) == _record_shape(unknown_records[0])
    assert wrong_records[0].getMessage() == unknown_records[0].getMessage()

    assert "conocido@example.com" not in wrong_records[0].getMessage()
    assert "desconocido@example.com" not in unknown_records[0].getMessage()
    # No identity leaks on a failed login, not even an opaque internal id.
    assert str(tenant.user.id) not in wrong_records[0].getMessage()
    assert str(tenant.user.id) != getattr(wrong_records[0], "user_id", None)


async def test_reused_refresh_token_is_logged_without_the_token_value(
    client, seed_tenant, fake_clock, caplog
):
    """A revoked/replayed refresh is recorded as a failure, token value absent."""
    await seed_tenant(email="refresco-log@example.com")
    first = await _login(client, "refresco-log@example.com")
    rotated = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200

    fake_clock.advance(REFRESH_REPLAY_GRACE.total_seconds() + 1)
    with caplog.at_level(logging.INFO, logger="app.auth"):
        replay = await client.post(
            REFRESH, json={"refresh_token": first["refresh_token"]}
        )

    assert replay.status_code == 401
    failures = [
        record
        for record in _auth_records(caplog)
        if getattr(record, "event", None) == "auth.refresh"
        and getattr(record, "result", None) == "failure"
    ]
    assert failures, "a rejected refresh must leave an operational log entry"
    assert getattr(failures[-1], "reason", None) == "reuse"

    logged = "\n".join(
        f"{record.getMessage()} {record.__dict__!r}" for record in failures
    )
    assert first["refresh_token"] not in logged
    assert rotated.json()["refresh_token"] not in logged
    assert "refresco-log@example.com" not in logged


async def test_login_payload_validation_returns_422(client):
    response = await client.post(LOGIN, json={"email": "not-an-email"})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def _login(client, email: str = "admin@example.com") -> dict[str, str]:
    response = await client.post(LOGIN, json={"email": email, "password": "Secreta-123"})
    assert response.status_code == 200, response.text
    return response.json()


async def test_refresh_rotates_the_token(client, seed_tenant):
    await seed_tenant(email="rotar@example.com")
    first = await _login(client, "rotar@example.com")

    response = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type", "role"}
    assert body["refresh_token"] != first["refresh_token"]
    new_claims = decode_access_token(body["access_token"])
    first_claims = decode_access_token(first["access_token"])
    assert new_claims["sub"] == first_claims["sub"]
    assert new_claims["jti"] != first_claims["jti"]


async def test_previous_refresh_is_no_longer_usable(client, seed_tenant):
    """Spec: the previous token stops working after rotation."""
    await seed_tenant(email="viejo@example.com")
    first = await _login(client, "viejo@example.com")
    rotated = await client.post(
        REFRESH, json={"refresh_token": first["refresh_token"]}
    )
    assert rotated.status_code == 200
    successor = rotated.json()["refresh_token"]

    replay = await client.post(
        REFRESH, json={"refresh_token": first["refresh_token"]}
    )

    assert replay.status_code == 401
    assert replay.json()["code"] == "session_revoked"
    # Inside the grace window the legitimate successor stays alive (D3 Risks).
    assert (
        await client.post(REFRESH, json={"refresh_token": successor})
    ).status_code == 200


async def test_unknown_refresh_token_is_rejected(client):
    response = await client.post(REFRESH, json={"refresh_token": "no-existe"})

    assert response.status_code == 401
    assert response.json()["code"] == "session_revoked"


async def test_refresh_payload_requires_the_token(client):
    response = await client.post(REFRESH, json={})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_refresh_rejects_a_deactivated_user(client, seed_tenant, test_session):
    tenant = await seed_tenant(email="baja-refresh@example.com")
    first = await _login(client, "baja-refresh@example.com")
    tenant.user.is_active = False
    await test_session.flush()

    response = await client.post(
        REFRESH, json={"refresh_token": first["refresh_token"]}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_refresh_rejects_an_inactive_clinic(client, seed_tenant, test_session):
    tenant = await seed_tenant(email="clinica-refresh@example.com")
    first = await _login(client, "clinica-refresh@example.com")
    tenant.clinic.is_active = False
    await test_session.flush()

    response = await client.post(
        REFRESH, json={"refresh_token": first["refresh_token"]}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert first["refresh_token"] not in response.text


async def test_double_concurrent_refresh_keeps_the_session_alive(
    client, seed_tenant, fake_clock
):
    """Design Risks: a racing retry must not revoke a legitimate session."""
    await seed_tenant(email="doble@example.com")
    first = await _login(client, "doble@example.com")
    winner = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    assert winner.status_code == 200

    fake_clock.advance(1)
    loser = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert loser.status_code == 401
    assert loser.json()["code"] == "session_revoked"
    recovered = await client.post(
        REFRESH, json={"refresh_token": winner.json()["refresh_token"]}
    )
    assert recovered.status_code == 200


async def test_reuse_after_the_grace_window_revokes_the_whole_family(
    client, seed_tenant, fake_clock, test_session
):
    """Spec: presenting an already-rotated token kills the family (D3)."""
    tenant = await seed_tenant(email="reuso@example.com")
    first = await _login(client, "reuso@example.com")
    rotated = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    successor = rotated.json()["refresh_token"]
    assert rotated.status_code == 200

    fake_clock.advance(REFRESH_REPLAY_GRACE.total_seconds() + 1)
    replay = await client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert replay.status_code == 401
    assert replay.json()["code"] == "session_revoked"

    # The whole family is revoked, including the token issued by the rotation.
    assert (
        await client.post(REFRESH, json={"refresh_token": successor})
    ).status_code == 401

    rows = (
        await test_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == tenant.user.id)
        )
    ).scalars().all()
    assert rows
    assert all(row.revoked_at is not None for row in rows)


async def test_expired_refresh_token_is_rejected(client, seed_tenant, fake_clock):
    await seed_tenant(email="expirado@example.com")
    first = await _login(client, "expirado@example.com")

    fake_clock.advance(8 * 24 * 60 * 60)  # defaults: 7-day refresh lifetime

    response = await client.post(
        REFRESH, json={"refresh_token": first["refresh_token"]}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "session_revoked"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_logout_revokes_the_refresh_session(client, seed_tenant):
    await seed_tenant(email="logout@example.com")
    session = await _login(client, "logout@example.com")

    logout = await client.post(
        LOGOUT,
        json={"refresh_token": session["refresh_token"]},
        headers=_auth(session["access_token"]),
    )
    assert logout.status_code == 204
    assert logout.content == b""

    after = await client.post(
        REFRESH, json={"refresh_token": session["refresh_token"]}
    )
    assert after.status_code == 401
    assert after.json()["code"] == "session_revoked"


async def test_logout_requires_authentication(client, seed_tenant):
    await seed_tenant(email="logout-anon@example.com")
    session = await _login(client, "logout-anon@example.com")

    response = await client.post(
        LOGOUT, json={"refresh_token": session["refresh_token"]}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"
    # The unauthenticated attempt changed nothing.
    assert (
        await client.post(REFRESH, json={"refresh_token": session["refresh_token"]})
    ).status_code == 200


async def test_logout_cannot_revoke_another_users_session(client, seed_tenant):
    await seed_tenant(email="atacante@example.com")
    await seed_tenant(email="victima@example.com")
    attacker_session = await _login(client, "atacante@example.com")
    victim_session = await _login(client, "victima@example.com")

    response = await client.post(
        LOGOUT,
        json={"refresh_token": victim_session["refresh_token"]},
        headers=_auth(attacker_session["access_token"]),
    )

    assert response.status_code == 401
    assert response.json()["code"] == "session_revoked"
    # The victim's session is untouched.
    assert (
        await client.post(
            REFRESH, json={"refresh_token": victim_session["refresh_token"]}
        )
    ).status_code == 200


async def test_me_returns_only_the_caller_profile(client, seed_tenant):
    tenant = await seed_tenant(role="dentist", email="perfil@example.com")
    session = await _login(client, "perfil@example.com")

    response = await client.get(ME, headers=_auth(session["access_token"]))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "full_name", "role", "is_active", "clinic"}
    assert body["id"] == str(tenant.user.id)
    assert body["email"] == "perfil@example.com"
    assert body["role"] == "dentist"
    assert body["clinic"] == {
        "id": str(tenant.clinic.id),
        "name": tenant.clinic.name,
        "slug": tenant.clinic.slug,
    }
    assert "password" not in response.text.lower()
    assert "token" not in response.text.lower()
    assert session["refresh_token"] not in response.text


async def test_me_cannot_be_targeted_at_another_user(client, seed_tenant):
    await seed_tenant(email="yo@example.com")
    other = await seed_tenant(email="otro@example.com")
    session = await _login(client, "yo@example.com")

    response = await client.get(
        ME, params={"user_id": str(other.user.id)}, headers=_auth(session["access_token"])
    )

    assert response.status_code == 200
    assert response.json()["email"] == "yo@example.com"
    assert str(other.user.id) not in response.text


async def test_me_requires_a_valid_token(client):
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_password_change_replaces_the_credential(client, seed_tenant):
    """Spec: the old password stops working, the new one starts working."""
    await seed_tenant(email="cambio@example.com")
    session = await _login(client, "cambio@example.com")

    response = await client.patch(
        PASSWORD,
        json={"current_password": "Secreta-123", "new_password": "Nueva-Clave-456"},
        headers=_auth(session["access_token"]),
    )

    assert response.status_code == 204
    old = await client.post(
        LOGIN, json={"email": "cambio@example.com", "password": "Secreta-123"}
    )
    new = await client.post(
        LOGIN, json={"email": "cambio@example.com", "password": "Nueva-Clave-456"}
    )
    assert old.status_code == 401
    assert new.status_code == 200


async def test_password_change_revokes_other_sessions(client, seed_tenant):
    await seed_tenant(email="sesiones@example.com")
    first = await _login(client, "sesiones@example.com")
    second = await _login(client, "sesiones@example.com")

    response = await client.patch(
        PASSWORD,
        json={"current_password": "Secreta-123", "new_password": "Nueva-Clave-456"},
        headers=_auth(first["access_token"]),
    )
    assert response.status_code == 204

    other = await client.post(
        REFRESH, json={"refresh_token": second["refresh_token"]}
    )
    assert other.status_code == 401
    assert other.json()["code"] == "session_revoked"

    # The caller's access token keeps working until it expires (stateless JWT).
    me = await client.get(ME, headers=_auth(first["access_token"]))
    assert me.status_code == 200


async def test_password_change_requires_the_current_password(client, seed_tenant):
    await seed_tenant(email="actual@example.com")
    session = await _login(client, "actual@example.com")

    response = await client.patch(
        PASSWORD,
        json={"current_password": "equivocada", "new_password": "Nueva-Clave-456"},
        headers=_auth(session["access_token"]),
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    # Nothing changed: the original password still authenticates.
    assert (
        await client.post(
            LOGIN, json={"email": "actual@example.com", "password": "Secreta-123"}
        )
    ).status_code == 200


async def test_password_change_requires_authentication(client):
    response = await client.patch(
        PASSWORD,
        json={"current_password": "Secreta-123", "new_password": "Nueva-Clave-456"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_short_new_password_is_rejected(client, seed_tenant):
    await seed_tenant(email="corta@example.com")
    session = await _login(client, "corta@example.com")

    response = await client.patch(
        PASSWORD,
        json={"current_password": "Secreta-123", "new_password": "corta"},
        headers=_auth(session["access_token"]),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
