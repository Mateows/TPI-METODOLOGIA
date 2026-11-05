"""Task 3.2 — per-request identity resolution (design D2/D4).

The token only *indicates* identity: the server reloads ``User`` + ``Clinic``
on every request, rejects an inactive account with 401 and an inactive clinic
with 403.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_principal
from app.core.database import get_db
from app.core.errors import register_exception_handlers
from app.core.security import create_access_token, hash_password
from app.models.clinic import Clinic
from app.models.user import User
from app.services.principal import Principal


@dataclass
class Seeded:
    clinic: Clinic
    user: User

    def token(self, *, clinic_id: str | None = None, expires_delta: timedelta | None = None) -> str:
        return create_access_token(
            subject=str(self.user.id),
            clinic_id=clinic_id or str(self.clinic.id),
            role=self.user.role,
            expires_delta=expires_delta,
        )


@pytest.fixture()
async def seeded(test_session) -> Seeded:
    clinic = Clinic(name="Clinica Norte", slug="norte", tax_id="30-11111111-1")
    test_session.add(clinic)
    await test_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="recepcion@example.com",
        password_hash=hash_password("Secreta-123"),
        full_name="Rita Recepcionista",
        role="receptionist",
    )
    test_session.add(user)
    await test_session.flush()
    return Seeded(clinic=clinic, user=user)


@pytest.fixture()
async def guarded_client(test_session) -> AsyncIterator[AsyncClient]:
    """Minimal protected app: the dependency under test, nothing else."""
    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/whoami")
    async def whoami(principal: Principal = Depends(get_current_principal)) -> dict[str, str]:
        return {
            "user_id": str(principal.user_id),
            "clinic_id": str(principal.clinic_id),
            "role": principal.role,
        }

    async def _override() -> AsyncIterator[object]:
        yield test_session

    application.dependency_overrides[get_db] = _override
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as http:
        yield http


async def test_valid_token_resolves_principal_from_the_database(guarded_client, seeded):
    """WHEN a valid bearer token arrives THEN identity comes from the loaded rows."""
    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {seeded.token()}"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(seeded.user.id),
        "clinic_id": str(seeded.clinic.id),
        "role": "receptionist",
    }


async def test_missing_authorization_header_is_rejected(guarded_client):
    response = await guarded_client.get("/whoami")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_expired_token_is_rejected(guarded_client, seeded):
    """WHEN exp is in the past THEN 401 and no identity is returned."""
    token = seeded.token(expires_delta=timedelta(minutes=-1))

    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_deactivated_user_is_rejected_even_with_a_valid_token(
    guarded_client, seeded, test_session
):
    """D4: deactivation must bite on the very next request (spec scenario)."""
    seeded.user.is_active = False
    await test_session.flush()

    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {seeded.token()}"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"
    assert "user_id" not in response.json()


async def test_inactive_clinic_gets_403_not_401(guarded_client, seeded, test_session):
    """D4: the session is authentic but the tenant cannot operate → 403."""
    seeded.clinic.is_active = False
    await test_session.flush()

    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {seeded.token()}"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert str(seeded.clinic.id) not in response.text


async def test_token_clinic_claim_must_match_the_loaded_user(guarded_client, seeded):
    """A stale token for a user who changed clinic is not trusted (D4)."""
    stale = seeded.token(clinic_id="00000000-0000-4000-8000-000000000999")

    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {stale}"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_token_for_unknown_user_is_rejected(guarded_client, seeded):
    ghost = create_access_token(
        subject="00000000-0000-4000-8000-000000000111",
        clinic_id=str(seeded.clinic.id),
        role="admin",
    )

    response = await guarded_client.get(
        "/whoami", headers={"Authorization": f"Bearer {ghost}"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"
