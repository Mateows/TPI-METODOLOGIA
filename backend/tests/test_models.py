"""Task 2.1 — schema contract for Clinic, User and RefreshToken.

Uses an isolated in-memory SQLite schema (create_all) so these tests prove the
model contract independently of the Alembic migration that task 2.2 adds.
Design D12: the agenda professional is a User with role ``dentist``; there is no
separate Professional entity.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool

from app.core.database import Base, utcnow
from app.models.clinic import Clinic
from app.models.refresh_token import RefreshToken
from app.models.user import USER_ROLES, User


@pytest.fixture()
async def schema_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


def _clinic(**overrides) -> Clinic:
    values = {"name": "Clinica Norte", "slug": "clinica-norte", "tax_id": "30-11111111-1"}
    values.update(overrides)
    return Clinic(**values)


def _user(clinic: Clinic, **overrides) -> User:
    values = {
        "clinic": clinic,
        "email": "admin@example.com",
        "password_hash": "$2b$12$" + "x" * 53,
        "full_name": "Ada Administradora",
        "role": "admin",
    }
    values.update(overrides)
    return User(**values)


def test_metadata_registers_tables_with_deterministic_names():
    """WHEN models are imported THEN Base.metadata holds named tables/constraints."""
    tables = Base.metadata.tables
    assert {"clinics", "users", "refresh_tokens"} <= set(tables)
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert tables["users"].primary_key.name == "pk_users"
    assert "professional" not in tables  # D12: no parallel professional entity


def test_clinic_has_expected_columns_and_unique_slug():
    columns = {c.name for c in Base.metadata.tables["clinics"].columns}
    assert {
        "id",
        "name",
        "slug",
        "tax_id",
        "address",
        "phone",
        "is_active",
        "created_at",
        "updated_at",
    } <= columns
    assert Base.metadata.tables["clinics"].c.slug.unique is True
    assert Base.metadata.tables["clinics"].c.tax_id.unique is True


def test_user_has_expected_columns_and_tenant_index():
    users = Base.metadata.tables["users"]
    assert {
        "id",
        "clinic_id",
        "email",
        "password_hash",
        "full_name",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    } <= {c.name for c in users.columns}
    assert users.c.email.unique is True
    assert users.c.clinic_id.index is True
    assert users.c.clinic_id.nullable is False
    uq_names = {c.name for c in users.constraints if c.name}
    assert "uq_users_email" in uq_names


def test_refresh_token_has_family_and_rotation_columns():
    tokens = Base.metadata.tables["refresh_tokens"]
    assert {
        "id",
        "user_id",
        "clinic_id",
        "family_id",
        "token_hash",
        "issued_at",
        "expires_at",
        "rotated_at",
        "revoked_at",
        "replaced_by_id",
    } <= {c.name for c in tokens.columns}
    assert tokens.c.token_hash.unique is True
    assert tokens.c.user_id.index is True
    assert tokens.c.family_id.index is True
    assert tokens.c.clinic_id.index is True


def test_roles_are_limited_and_dentist_is_the_professional():
    """D12: dentists are Users; the role set is closed and has no 'professional'."""
    assert set(USER_ROLES) == {"admin", "receptionist", "dentist"}


async def test_email_is_normalized_to_lowercase_on_assignment(schema_session):
    clinic = _clinic()
    schema_session.add(clinic)
    await schema_session.flush()

    user = _user(clinic, email="  Admin@Example.COM  ")
    schema_session.add(user)
    await schema_session.flush()

    assert user.email == "admin@example.com"


async def test_duplicate_email_is_rejected_by_the_database(schema_session):
    """D6: email identity is unique across clinics, not per clinic."""
    first_clinic = _clinic()
    second_clinic = _clinic(name="Clinica Sur", slug="clinica-sur", tax_id="30-22222222-2")
    schema_session.add_all([first_clinic, second_clinic])
    await schema_session.flush()

    schema_session.add(_user(first_clinic, email="same@example.com", role="admin"))
    await schema_session.flush()

    schema_session.add(_user(second_clinic, email="SAME@example.com", role="dentist"))
    with pytest.raises(IntegrityError):
        await schema_session.flush()


async def test_duplicate_clinic_slug_is_rejected_by_the_database(schema_session):
    schema_session.add(_clinic(slug="repetido", tax_id="30-33333333-3"))
    await schema_session.flush()

    schema_session.add(_clinic(name="Otra", slug="repetido", tax_id="30-44444444-4"))
    with pytest.raises(IntegrityError):
        await schema_session.flush()


async def test_unknown_role_is_rejected_by_the_check_constraint(schema_session):
    clinic = _clinic()
    schema_session.add(clinic)
    await schema_session.flush()

    schema_session.add(_user(clinic, role="professional"))
    with pytest.raises(IntegrityError):
        await schema_session.flush()


async def test_relationships_link_clinic_user_and_refresh_tokens(schema_session):
    clinic = _clinic()
    user = _user(clinic, role="dentist")
    schema_session.add_all([clinic, user])
    await schema_session.flush()

    schema_session.add(
        RefreshToken(
            user=user,
            clinic_id=clinic.id,
            family_id=user.id,
            token_hash="a" * 64,
            issued_at=utcnow(),
            expires_at=utcnow() + timedelta(days=7),
        )
    )
    await schema_session.flush()

    loaded = (
        await schema_session.execute(
            select(User)
            .options(selectinload(User.refresh_tokens), selectinload(User.clinic))
            .where(User.email == "admin@example.com")
        )
    ).scalar_one()
    assert loaded.clinic.id == clinic.id
    assert loaded.role == "dentist"  # D12: dentist user is the professional
    assert [t.token_hash for t in loaded.refresh_tokens] == ["a" * 64]


async def test_timestamps_default_to_utc_aware_now(schema_session):
    clinic = _clinic()
    schema_session.add(clinic)
    await schema_session.flush()

    assert clinic.created_at is not None
    assert clinic.updated_at >= clinic.created_at
    assert Base.metadata.tables["clinics"].c.created_at.type.timezone is True
    assert utcnow().tzinfo is UTC
    assert isinstance(utcnow(), datetime)
