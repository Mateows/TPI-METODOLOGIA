"""Task 8.2 — repository layer unit tests (design D13).

Repositories own every SQLAlchemy query. They only ``flush`` (never commit) and
every clinic-scoped read takes ``clinic_id`` explicitly, so a row of another
clinic is never returned (design D5). Global lookups are the ones needed before
a ``Principal`` exists (login by email, refresh by hash, email uniqueness D6,
bootstrap) and are named as such.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import utcnow
from app.core.security import hash_refresh_token
from app.models.clinic import Clinic
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.clinics import ClinicRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository


def _user(clinic_id: uuid.UUID, email: str, *, role: str = "dentist", active: bool = True) -> User:
    return User(
        clinic_id=clinic_id,
        email=email,
        password_hash="$2b$12$" + "x" * 53,
        full_name="Usuario Repo",
        role=role,
        is_active=active,
    )


def _token(user: User, family_id: uuid.UUID, raw: str) -> RefreshToken:
    issued_at = utcnow()
    return RefreshToken(
        user_id=user.id,
        clinic_id=user.clinic_id,
        family_id=family_id,
        token_hash=hash_refresh_token(raw),
        issued_at=issued_at,
        expires_at=issued_at + timedelta(days=7),
    )


# --------------------------------------------------------------------- users


async def test_get_with_clinic_by_email_returns_the_pair(seed_tenant, test_session):
    tenant = await seed_tenant(email="pair@example.com")

    row = await UserRepository(test_session).get_with_clinic_by_email("pair@example.com")

    assert row is not None
    user, clinic = row
    assert user.id == tenant.user.id
    assert clinic.id == tenant.clinic.id


async def test_get_with_clinic_by_email_unknown_is_none(seed_tenant, test_session):
    await seed_tenant(email="known@example.com")

    assert await UserRepository(test_session).get_with_clinic_by_email("ghost@example.com") is None


async def test_get_with_clinic_by_id_returns_the_pair_or_none(seed_tenant, test_session):
    tenant = await seed_tenant()
    repo = UserRepository(test_session)

    row = await repo.get_with_clinic_by_id(tenant.user.id)

    assert row is not None
    assert (row[0].id, row[1].id) == (tenant.user.id, tenant.clinic.id)
    assert await repo.get_with_clinic_by_id(uuid.uuid4()) is None


async def test_email_exists_is_global(seed_tenant, test_session):
    await seed_tenant(email="taken@example.com")
    repo = UserRepository(test_session)

    assert await repo.email_exists("taken@example.com") is True
    assert await repo.email_exists("free@example.com") is False


async def test_add_flushes_and_assigns_an_id(seed_tenant, test_session):
    tenant = await seed_tenant()
    repo = UserRepository(test_session)

    user = await repo.add(_user(tenant.clinic.id, "new-member@example.com"))

    assert user.id is not None
    assert await repo.email_exists("new-member@example.com") is True


async def test_add_duplicate_raises_without_poisoning_the_transaction(seed_tenant, test_session):
    """The savepoint keeps the outer transaction usable after a raced duplicate."""
    tenant = await seed_tenant(email="dup@example.com")
    repo = UserRepository(test_session)

    with pytest.raises(IntegrityError):
        await repo.add(_user(tenant.clinic.id, "dup@example.com"))

    # The request transaction is still alive: further work succeeds.
    other = await repo.add(_user(tenant.clinic.id, "after-dup@example.com"))
    assert other.id is not None


async def test_list_for_clinic_never_returns_foreign_rows(seed_tenant, test_session):
    own = await seed_tenant(email="b-own@example.com")
    foreign = await seed_tenant(email="foreign@example.com")
    repo = UserRepository(test_session)
    await repo.add(_user(own.clinic.id, "a-own@example.com"))

    rows = await repo.list_for_clinic(own.clinic.id)

    assert [row.email for row in rows] == ["a-own@example.com", "b-own@example.com"]
    assert foreign.user.id not in {row.id for row in rows}


async def test_list_for_clinic_of_unknown_clinic_is_empty(seed_tenant, test_session):
    await seed_tenant()

    assert await UserRepository(test_session).list_for_clinic(uuid.uuid4()) == []


async def test_get_in_clinic_foreign_is_indistinguishable_from_absent(seed_tenant, test_session):
    own = await seed_tenant()
    foreign = await seed_tenant()
    repo = UserRepository(test_session)

    found = await repo.get_in_clinic(own.clinic.id, own.user.id)
    foreign_row = await repo.get_in_clinic(own.clinic.id, foreign.user.id)
    absent_row = await repo.get_in_clinic(own.clinic.id, uuid.uuid4())

    assert found is not None and found.id == own.user.id
    assert foreign_row is None
    assert foreign_row == absent_row


async def test_count_other_active_admins_excludes_self_inactive_and_other_clinics(
    seed_tenant, test_session
):
    own = await seed_tenant(role="admin")
    foreign = await seed_tenant(role="admin")
    repo = UserRepository(test_session)
    await repo.add(_user(own.clinic.id, "inactive-admin@example.com", role="admin", active=False))
    await repo.add(_user(own.clinic.id, "dentist@example.com", role="dentist"))

    # Only self is an active admin of the clinic; foreign admins never count.
    assert await repo.count_other_active_admins(own.clinic.id, own.user.id) == 0
    assert await repo.count_other_active_admins(foreign.clinic.id, foreign.user.id) == 0


async def test_count_other_active_admins_counts_peers(seed_tenant, test_session):
    own = await seed_tenant(role="admin")
    repo = UserRepository(test_session)
    peer = await repo.add(_user(own.clinic.id, "peer-admin@example.com", role="admin"))

    assert await repo.count_other_active_admins(own.clinic.id, own.user.id) == 1
    assert await repo.count_other_active_admins(own.clinic.id, peer.id) == 1


# ------------------------------------------------------------ refresh tokens


async def test_refresh_add_and_get_with_account_by_hash(seed_tenant, test_session):
    tenant = await seed_tenant()
    repo = RefreshTokenRepository(test_session)

    token = await repo.add(_token(tenant.user, uuid.uuid4(), "raw-value-1"))
    row = await repo.get_with_account_by_hash(hash_refresh_token("raw-value-1"))

    assert token.id is not None
    assert row is not None
    token_row, user, clinic = row
    assert (token_row.id, user.id, clinic.id) == (token.id, tenant.user.id, tenant.clinic.id)


async def test_refresh_get_by_unknown_hash_is_none(seed_tenant, test_session):
    tenant = await seed_tenant()
    repo = RefreshTokenRepository(test_session)
    await repo.add(_token(tenant.user, uuid.uuid4(), "raw-value-2"))

    assert await repo.get_with_account_by_hash(hash_refresh_token("other")) is None


async def test_revoke_family_only_touches_that_family_and_unrevoked_rows(
    seed_tenant, test_session
):
    tenant = await seed_tenant()
    repo = RefreshTokenRepository(test_session)
    family, other_family = uuid.uuid4(), uuid.uuid4()
    live = await repo.add(_token(tenant.user, family, "f-live"))
    already = await repo.add(_token(tenant.user, family, "f-already"))
    earlier = utcnow() - timedelta(days=1)
    already.revoked_at = earlier
    bystander = await repo.add(_token(tenant.user, other_family, "o-live"))
    revoked_at = utcnow()

    revoked = await repo.revoke_family(family, revoked_at)

    assert revoked == 1
    assert live.revoked_at == revoked_at
    assert already.revoked_at == earlier
    assert bystander.revoked_at is None


async def test_revoke_family_of_unknown_family_is_a_noop(seed_tenant, test_session):
    tenant = await seed_tenant()
    repo = RefreshTokenRepository(test_session)
    row = await repo.add(_token(tenant.user, uuid.uuid4(), "noop"))

    assert await repo.revoke_family(uuid.uuid4(), utcnow()) == 0
    assert row.revoked_at is None


async def test_revoke_all_for_user_spares_other_users(seed_tenant, test_session):
    target = await seed_tenant()
    other = await seed_tenant()
    repo = RefreshTokenRepository(test_session)
    first = await repo.add(_token(target.user, uuid.uuid4(), "t-1"))
    second = await repo.add(_token(target.user, uuid.uuid4(), "t-2"))
    spared = await repo.add(_token(other.user, uuid.uuid4(), "o-1"))
    revoked_at = utcnow()

    revoked = await repo.revoke_all_for_user(target.user.id, revoked_at)

    assert revoked == 2
    assert first.revoked_at == revoked_at
    assert second.revoked_at == revoked_at
    assert spared.revoked_at is None


async def test_revoke_all_for_user_keeps_earlier_revocations(seed_tenant, test_session):
    target = await seed_tenant()
    repo = RefreshTokenRepository(test_session)
    earlier = utcnow() - timedelta(hours=1)
    old = await repo.add(_token(target.user, uuid.uuid4(), "old"))
    old.revoked_at = earlier

    assert await repo.revoke_all_for_user(target.user.id, utcnow()) == 0
    assert old.revoked_at == earlier


# ------------------------------------------------------------------- clinics


async def test_clinic_add_and_get_by_tax_id(test_session):
    repo = ClinicRepository(test_session)

    clinic = await repo.add(
        Clinic(name="Clinica Repo", slug=f"repo-{uuid.uuid4().hex[:8]}", tax_id="30-99999999-1")
    )

    found = await repo.get_by_tax_id("30-99999999-1")
    assert clinic.id is not None
    assert found is not None and found.id == clinic.id
    assert await repo.get_by_tax_id("30-00000000-0") is None


async def test_clinic_slug_exists(seed_tenant, test_session):
    tenant = await seed_tenant(clinic_slug="slug-ocupado")
    repo = ClinicRepository(test_session)

    assert tenant.clinic.slug == "slug-ocupado"
    assert await repo.slug_exists("slug-ocupado") is True
    assert await repo.slug_exists("slug-libre") is False


# ------------------------------------------------------------------ patients


def _patient_scope(tenant):
    from app.services.principal import Principal

    return Principal(
        user_id=tenant.user.id,
        clinic_id=tenant.clinic.id,
        role=tenant.user.role,
        user=tenant.user,
        clinic=tenant.clinic,
    )


def _patient(
    clinic_id: uuid.UUID,
    *,
    first_name: str = "Maria",
    last_name: str = "Suarez",
    dni: str = "30111222",
    is_active: bool = True,
):
    from app.models.patient import Patient

    return Patient(
        clinic_id=clinic_id,
        first_name=first_name,
        last_name=last_name,
        dni=dni,
        is_active=is_active,
    )


async def test_patient_repo_get_and_get_by_dni_never_return_foreign_clinic_rows(
    seed_tenant, test_session
):
    """Task 2.2: get and get_by_dni are strictly scoped to principal.clinic_id."""
    from app.repositories import PatientRepository

    own = await seed_tenant()
    foreign = await seed_tenant()
    own_repo = PatientRepository(test_session, _patient_scope(own))
    foreign_repo = PatientRepository(test_session, _patient_scope(foreign))

    own_patient = await own_repo.add(
        _patient(own.clinic.id, first_name="Ana", last_name="Paz", dni="31000111")
    )
    foreign_patient = await foreign_repo.add(
        _patient(
            foreign.clinic.id, first_name="Carlos", last_name="Rios", dni="32000222"
        )
    )

    assert (await own_repo.get(own_patient.id)) == own_patient
    assert (await own_repo.get(foreign_patient.id)) is None
    assert (await own_repo.get(uuid.uuid4())) is None

    assert (await own_repo.get_by_dni("31000111")) == own_patient
    assert (await own_repo.get_by_dni("32000222")) is None


async def test_patient_repo_dni_exists_and_savepoint_duplicate_handling(
    seed_tenant, test_session
):
    """Task 2.2 (triangulation): duplicate (clinic_id, dni) raises IntegrityError inside savepoint; same DNI in another clinic succeeds."""
    from app.repositories import PatientRepository

    own = await seed_tenant()
    foreign = await seed_tenant()
    own_repo = PatientRepository(test_session, _patient_scope(own))
    foreign_repo = PatientRepository(test_session, _patient_scope(foreign))

    created = await own_repo.add(_patient(own.clinic.id, dni="40123456"))
    assert await own_repo.dni_exists("40123456") is True
    assert await own_repo.dni_exists("40123456", exclude_id=created.id) is False
    assert await foreign_repo.dni_exists("40123456") is False

    # Same DNI in another clinic is allowed
    foreign_same_dni = await foreign_repo.add(
        _patient(foreign.clinic.id, dni="40123456")
    )
    assert foreign_same_dni.id is not None

    # Duplicate DNI in the same clinic raises IntegrityError without poisoning session
    with pytest.raises(IntegrityError):
        await own_repo.add(_patient(own.clinic.id, dni="40123456"))

    # Session remains usable after savepoint rollback
    after_dup = await own_repo.add(_patient(own.clinic.id, dni="40999999"))
    assert after_dup.id is not None

    # Updating another patient in the same clinic to a taken DNI also rolls back savepoint
    original_dni = after_dup.dni
    after_dup.dni = "40123456"
    with pytest.raises(IntegrityError):
        await own_repo.save(after_dup)
    after_dup.dni = original_dni


async def test_patient_repo_search_filters_by_query_active_status_and_pagination(
    seed_tenant, test_session
):
    """Task 2.2: search filters by clinic_id, active status, q (dni/first_name/last_name), and supports limit/offset."""
    from app.repositories import PatientRepository

    own = await seed_tenant()
    foreign = await seed_tenant()
    own_repo = PatientRepository(test_session, _patient_scope(own))
    foreign_repo = PatientRepository(test_session, _patient_scope(foreign))

    p1 = await own_repo.add(
        _patient(own.clinic.id, first_name="Lucia", last_name="Alvarez", dni="30100200")
    )
    p2 = await own_repo.add(
        _patient(own.clinic.id, first_name="Martin", last_name="Bianchi", dni="35999000")
    )
    p_inactive = await own_repo.add(
        _patient(
            own.clinic.id,
            first_name="Lucia",
            last_name="Zorro",
            dni="28000111",
            is_active=False,
        )
    )
    await foreign_repo.add(
        _patient(
            foreign.clinic.id,
            first_name="Lucia",
            last_name="Alvarez",
            dni="30100200",
        )
    )

    # Default excludes inactive and foreign patients, ordered by last_name, first_name
    active_rows = await own_repo.search()
    assert [r.id for r in active_rows] == [p1.id, p2.id]

    # include_inactive=True includes p_inactive
    all_rows = await own_repo.search(include_inactive=True)
    assert [r.id for r in all_rows] == [p1.id, p2.id, p_inactive.id]

    # Search by first_name, last_name, and dni (case-insensitive)
    assert [r.id for r in await own_repo.search("lucia")] == [p1.id]
    assert [r.id for r in await own_repo.search("BIANCHI")] == [p2.id]
    assert [r.id for r in await own_repo.search("35999")] == [p2.id]

    # Pagination
    paged = await own_repo.search(include_inactive=True, limit=1, offset=1)
    assert [r.id for r in paged] == [p2.id]
