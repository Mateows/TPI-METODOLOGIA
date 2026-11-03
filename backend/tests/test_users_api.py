"""Tasks 5.1–5.3 — intra-clinic user administration (design D5/D6/D10).

Contract under test:
* only an authenticated ``admin`` may create, list or update users;
* every operation is scoped to the admin's own clinic, derived from the token;
* a foreign user id answers exactly like an absent one (404, same body);
* a duplicate email answers 409 without disclosing the owning clinic;
* the clinic can never be left without an active administrator.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.user import User

USERS = "/api/v1/users"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_user(
    test_session,
    tenant,
    *,
    email: str,
    role: str = "dentist",
    full_name: str = "Persona Extra",
    is_active: bool = True,
) -> User:
    """Add a second account to ``tenant``'s clinic (outside the API)."""
    user = User(
        clinic_id=tenant.clinic.id,
        email=email,
        password_hash=hash_password("Secreta-123"),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    test_session.add(user)
    await test_session.flush()
    return user


async def _count_users(test_session, clinic_id: uuid.UUID) -> int:
    return (
        await test_session.execute(
            select(func.count()).select_from(User).where(User.clinic_id == clinic_id)
        )
    ).scalar_one()


# --------------------------------------------------------------------------- #
# 5.1 — create + list
# --------------------------------------------------------------------------- #


async def test_admin_creates_a_user_in_their_own_clinic(client, seed_tenant, test_session):
    admin = await seed_tenant(role="admin", email="admin-alta@example.com")

    response = await client.post(
        USERS,
        json={
            "email": "Nueva.Persona@Example.com",
            "full_name": "Nueva Persona",
            "role": "dentist",
            "password": "Inicial-123",
        },
        headers=_auth(admin.token()),
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "full_name", "role", "is_active"}
    assert body["email"] == "nueva.persona@example.com"  # normalized (D6)
    assert body["full_name"] == "Nueva Persona"
    assert body["role"] == "dentist"
    assert body["is_active"] is True
    # No credential material in the response.
    assert "Inicial-123" not in response.text
    assert "password" not in response.text.lower()

    created = await test_session.get(User, uuid.UUID(body["id"]))
    assert created is not None
    assert created.clinic_id == admin.clinic.id
    assert created.password_hash != "Inicial-123"
    assert created.password_hash.startswith(("$2a$", "$2b$", "$2y$"))

    # The assigned clinic is never taken from the request body.
    assert str(admin.clinic.id) not in response.text


async def test_create_referencing_a_foreign_clinic_is_rejected_without_persisting(
    client, seed_tenant, test_session
):
    """Spec tenant-isolation: a foreign reference is a validation error, no record.

    A client cannot pin the new user to another clinic by sending ``clinic_id``:
    the payload is rejected before any row is written to either clinic.
    """
    admin = await seed_tenant(role="admin", email="admin-referencia@example.com")
    foreign = await seed_tenant(role="dentist", email="ajena-referencia@example.com")
    before_own = await _count_users(test_session, admin.clinic.id)
    before_foreign = await _count_users(test_session, foreign.clinic.id)

    response = await client.post(
        USERS,
        json={
            "email": "referencia.ajena@example.com",
            "full_name": "Referencia Ajena",
            "role": "dentist",
            "password": "Inicial-123",
            "clinic_id": str(foreign.clinic.id),
        },
        headers=_auth(admin.token()),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await _count_users(test_session, admin.clinic.id) == before_own
    assert await _count_users(test_session, foreign.clinic.id) == before_foreign
    assert (
        await test_session.execute(
            select(User).where(User.email == "referencia.ajena@example.com")
        )
    ).first() is None


async def test_created_user_can_log_in_with_the_initial_password(
    client, seed_tenant
):
    admin = await seed_tenant(role="admin", email="admin-login-nuevo@example.com")
    created = await client.post(
        USERS,
        json={
            "email": "recien.creado@example.com",
            "full_name": "Recién Creado",
            "role": "receptionist",
            "password": "Inicial-123",
        },
        headers=_auth(admin.token()),
    )
    assert created.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "recien.creado@example.com", "password": "Inicial-123"},
    )

    assert login.status_code == 200
    assert login.json()["role"] == "receptionist"


async def test_invalid_role_is_rejected_without_creating_a_user(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-rol@example.com")
    before = await _count_users(test_session, admin.clinic.id)

    response = await client.post(
        USERS,
        json={
            "email": "rol.invalido@example.com",
            "full_name": "Rol Inválido",
            "role": "superuser",
            "password": "Inicial-123",
        },
        headers=_auth(admin.token()),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await _count_users(test_session, admin.clinic.id) == before


async def test_duplicate_email_conflicts_without_revealing_the_owner_clinic(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-duplicado@example.com")
    foreign = await seed_tenant(role="dentist", email="ocupado@example.com")
    before = await _count_users(test_session, admin.clinic.id)

    response = await client.post(
        USERS,
        json={
            "email": "  OCUPADO@Example.com ",
            "full_name": "Duplicado",
            "role": "dentist",
            "password": "Inicial-123",
        },
        headers=_auth(admin.token()),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_email"
    assert await _count_users(test_session, admin.clinic.id) == before
    # No tenant fingerprint in the conflict body (design D6).
    for secret in (foreign.clinic.name, foreign.clinic.slug, str(foreign.clinic.id)):
        assert secret not in response.text


async def test_listing_never_includes_users_of_another_clinic(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-lista@example.com")
    own_dentist = await _add_user(
        test_session, admin, email="propio@example.com", role="dentist"
    )
    foreign = await seed_tenant(role="dentist", email="ajeno@example.com")

    response = await client.get(USERS, headers=_auth(admin.token()))

    assert response.status_code == 200
    body = response.json()
    emails = {row["email"] for row in body}
    assert emails == {"admin-lista@example.com", "propio@example.com"}
    assert str(foreign.user.id) not in response.text
    assert "ajeno@example.com" not in response.text
    assert {row["id"] for row in body} == {
        str(admin.user.id),
        str(own_dentist.id),
    }


async def test_user_payload_requires_the_mandatory_fields(client, seed_tenant):
    admin = await seed_tenant(role="admin", email="admin-payload@example.com")

    missing_password = await client.post(
        USERS,
        json={
            "email": "sin.clave@example.com",
            "full_name": "Sin Clave",
            "role": "dentist",
        },
        headers=_auth(admin.token()),
    )
    extra_field = await client.post(
        USERS,
        json={
            "email": "con.extra@example.com",
            "full_name": "Con Extra",
            "role": "dentist",
            "password": "Inicial-123",
            "clinic_id": str(uuid.uuid4()),
        },
        headers=_auth(admin.token()),
    )

    assert missing_password.status_code == 422
    assert missing_password.json()["code"] == "validation_error"
    assert extra_field.status_code == 422


# --------------------------------------------------------------------------- #
# 5.2 — update
# --------------------------------------------------------------------------- #


async def test_admin_updates_name_role_and_state(client, seed_tenant, test_session):
    admin = await seed_tenant(role="admin", email="admin-patch@example.com")
    target = await _add_user(
        test_session, admin, email="objetivo@example.com", role="dentist"
    )

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"full_name": "Nombre Actualizado", "role": "receptionist"},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Nombre Actualizado"
    assert body["role"] == "receptionist"
    assert body["is_active"] is True

    await test_session.refresh(target)
    assert target.full_name == "Nombre Actualizado"
    assert target.role == "receptionist"


async def test_admin_deactivates_a_user(client, seed_tenant, test_session):
    admin = await seed_tenant(role="admin", email="admin-baja@example.com")
    target = await _add_user(test_session, admin, email="a.dar.de.baja@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"is_active": False},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    await test_session.refresh(target)
    assert target.is_active is False

    # The deactivated account can no longer authenticate (spec scenario).
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "a.dar.de.baja@example.com", "password": "Secreta-123"},
    )
    assert login.status_code == 401
    assert login.json()["code"] == "invalid_credentials"


async def test_admin_cannot_update_a_user_of_another_clinic(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-ajeno@example.com")
    foreign = await seed_tenant(role="dentist", email="victima@example.com")

    foreign_attempt = await client.patch(
        f"{USERS}/{foreign.user.id}",
        json={"full_name": "Secuestrado"},
        headers=_auth(admin.token()),
    )
    absent_attempt = await client.patch(
        f"{USERS}/{uuid.uuid4()}",
        json={"full_name": "Secuestrado"},
        headers=_auth(admin.token()),
    )

    assert foreign_attempt.status_code == absent_attempt.status_code == 404
    assert foreign_attempt.json() == absent_attempt.json()
    assert foreign_attempt.json()["code"] == "not_found"
    assert str(foreign.user.id) not in foreign_attempt.text

    await test_session.refresh(foreign.user)
    assert foreign.user.full_name != "Secuestrado"
    assert foreign.user.clinic_id == foreign.clinic.id


async def test_last_active_admin_cannot_demote_themselves(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="unico.admin@example.com")

    response = await client.patch(
        f"{USERS}/{admin.user.id}",
        json={"role": "dentist"},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_admin"
    await test_session.refresh(admin.user)
    assert admin.user.role == "admin"


async def test_last_active_admin_cannot_deactivate_themselves(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="unico.activo@example.com")

    response = await client.patch(
        f"{USERS}/{admin.user.id}",
        json={"is_active": False},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "last_admin"
    await test_session.refresh(admin.user)
    assert admin.user.is_active is True


async def test_admin_can_be_demoted_when_another_admin_remains(
    client, seed_tenant, test_session
):
    """Triangulation: the invariant is 'one active admin', not 'never self-demote'."""
    first = await seed_tenant(role="admin", email="primer.admin@example.com")
    second = await _add_user(
        test_session, first, email="segundo.admin@example.com", role="admin"
    )

    response = await client.patch(
        f"{USERS}/{second.id}",
        json={"role": "receptionist"},
        headers=_auth(first.token()),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "receptionist"

    # Deactivating the only remaining admin is still refused.
    blocked = await client.patch(
        f"{USERS}/{first.user.id}",
        json={"is_active": False},
        headers=_auth(first.token()),
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "last_admin"


async def test_update_rejects_an_unknown_role_and_persists_nothing(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-rol-patch@example.com")
    target = await _add_user(test_session, admin, email="intacto@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"role": "owner", "full_name": "No Debe Cambiar"},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    await test_session.refresh(target)
    assert target.role == "dentist"
    assert target.full_name == "Persona Extra"


# --------------------------------------------------------------------------- #
# 5.3 — non-admin roles
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("role", ["receptionist", "dentist"])
async def test_non_admin_roles_get_403_on_every_administration_endpoint(
    client, seed_tenant, test_session, role
):
    actor = await seed_tenant(role=role, email=f"{role}.actor@example.com")
    target = await _add_user(
        test_session, actor, email=f"{role}.objetivo@example.com"
    )
    before_users = await _count_users(test_session, actor.clinic.id)

    created = await client.post(
        USERS,
        json={
            "email": f"{role}.intento@example.com",
            "full_name": "Intento",
            "role": "dentist",
            "password": "Inicial-123",
        },
        headers=_auth(actor.token()),
    )
    listed = await client.get(USERS, headers=_auth(actor.token()))
    updated = await client.patch(
        f"{USERS}/{target.id}",
        json={"role": "admin", "is_active": False},
        headers=_auth(actor.token()),
    )

    for response in (created, listed, updated):
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"

    # No attempt persisted anything.
    assert await _count_users(test_session, actor.clinic.id) == before_users
    await test_session.refresh(target)
    assert target.role == "dentist"
    assert target.is_active is True


async def test_administration_endpoints_require_authentication(client):
    responses = [
        await client.post(
            USERS,
            json={
                "email": "anon@example.com",
                "full_name": "Anónimo",
                "role": "dentist",
                "password": "Inicial-123",
            },
        ),
        await client.get(USERS),
        await client.patch(f"{USERS}/{uuid.uuid4()}", json={"is_active": False}),
    ]

    for response in responses:
        assert response.status_code == 401
        assert response.json()["code"] == "authentication_failed"
