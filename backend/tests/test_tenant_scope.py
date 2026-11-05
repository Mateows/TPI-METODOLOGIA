"""Task 3.3 — RBAC guards and tenant-scoped persistence (design D5).

Two properties are proven here:
* a forbidden role is denied *before* any side effect;
* a record of another clinic is indistinguishable from an absent one.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.errors import TenantViolation, register_exception_handlers
from app.models.user import User
from app.services.principal import Principal
from app.services.tenant import TenantScopedRepository, resolve_clinic_id


def _principal(tenant) -> Principal:
    return Principal(
        user_id=tenant.user.id,
        clinic_id=tenant.clinic.id,
        role=tenant.user.role,
        user=tenant.user,
        clinic=tenant.clinic,
    )


@pytest.fixture()
async def guarded_app(test_session) -> AsyncIterator[AsyncClient]:
    """Admin-only endpoint that creates a user (a measurable side effect)."""
    application = FastAPI()
    register_exception_handlers(application)

    async def _create_teammate(
        principal: Principal = Depends(require_roles("admin")),
    ) -> dict[str, str]:
        teammate = User(
            clinic_id=principal.clinic_id,
            email=f"new-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$2b$12$" + "x" * 53,
            full_name="Nuevo Usuario",
            role="dentist",
        )
        test_session.add(teammate)
        await test_session.flush()
        return {"email": teammate.email}

    async def _override() -> AsyncIterator[object]:
        yield test_session

    application.add_api_route("/admin/users", _create_teammate, methods=["POST"])
    application.dependency_overrides[get_db] = _override
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as http:
        yield http


async def test_allowed_role_proceeds_and_persists(guarded_app, seed_tenant, test_session):
    admin = await seed_tenant(role="admin")

    response = await guarded_app.post(
        "/admin/users", headers={"Authorization": f"Bearer {admin.token()}"}
    )

    assert response.status_code == 200
    count = (
        await test_session.execute(
            select(func.count()).select_from(User).where(User.clinic_id == admin.clinic.id)
        )
    ).scalar_one()
    assert count == 2


@pytest.mark.parametrize("role", ["receptionist", "dentist"])
async def test_forbidden_role_is_denied_without_side_effects(
    guarded_app, seed_tenant, test_session, role
):
    """WHEN a non-admin calls an admin endpoint THEN 403 and nothing is written."""
    user = await seed_tenant(role=role)
    before = (
        await test_session.execute(select(func.count()).select_from(User))
    ).scalar_one()

    response = await guarded_app.post(
        "/admin/users", headers={"Authorization": f"Bearer {user.token()}"}
    )

    after = (
        await test_session.execute(select(func.count()).select_from(User))
    ).scalar_one()
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert after == before


def test_require_roles_rejects_unknown_role_names_at_definition_time():
    """A typo must fail fast instead of silently allowing/denying everything."""
    with pytest.raises(ValueError):
        require_roles("administrator")


async def test_repository_reads_own_clinic_record(seed_tenant, test_session):
    own = await seed_tenant(role="dentist")
    repo = TenantScopedRepository(User, test_session, _principal(own))

    found = await repo.get(own.user.id)

    assert found is not None
    assert found.id == own.user.id
    assert found.clinic_id == own.clinic.id


async def test_foreign_record_is_indistinguishable_from_absent(seed_tenant, test_session):
    """WHEN the id belongs to another clinic THEN the result equals a ghost id."""
    own = await seed_tenant(role="admin")
    foreign = await seed_tenant(role="dentist")
    repo = TenantScopedRepository(User, test_session, _principal(own))

    foreign_record = await repo.get(foreign.user.id)
    absent_record = await repo.get(uuid.uuid4())

    assert foreign_record is None
    assert foreign_record == absent_record


async def test_repository_listing_never_crosses_the_clinic_boundary(seed_tenant, test_session):
    own = await seed_tenant(role="admin")
    await seed_tenant(role="dentist")
    await seed_tenant(role="receptionist")
    repo = TenantScopedRepository(User, test_session, _principal(own))

    rows = await repo.list()

    assert [row.clinic_id for row in rows] == [own.clinic.id]
    assert {row.clinic_id for row in rows} == {own.clinic.id}


async def test_client_supplied_clinic_id_is_never_trusted(seed_tenant):
    """A mismatching clinic_id is rejected; a matching one is a no-op."""
    own = await seed_tenant(role="admin")
    principal = _principal(own)

    assert resolve_clinic_id(principal, None) == own.clinic.id
    assert resolve_clinic_id(principal, own.clinic.id) == own.clinic.id

    with pytest.raises(TenantViolation):
        resolve_clinic_id(principal, uuid.uuid4())

    with pytest.raises(TenantViolation) as excinfo:
        resolve_clinic_id(principal, uuid.uuid4())
    assert excinfo.value.status_code == 404
    assert excinfo.value.code == "not_found"


async def test_repository_rejects_models_without_a_clinic_scope():
    """A non-tenant model must not silently bypass isolation (fail loudly)."""

    class _NotScoped:
        __tablename__ = "not_scoped"

        id = None

    with pytest.raises(TypeError):
        TenantScopedRepository(_NotScoped, None, None)  # type: ignore[arg-type]
