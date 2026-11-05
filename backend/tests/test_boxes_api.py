"""C-04 task 2.1 — boxes slice (spec: appointment-agenda).

Contract under test:
* ``POST /api/v1/boxes`` creates a box inside the caller's clinic; the tenant
  comes only from the verified session (a payload ``clinic_id`` is a 422);
* only an ``admin`` may create boxes; every authenticated role may list/read;
* ``GET /api/v1/boxes`` lists the caller's boxes (all statuses by default, with
  an optional ``status`` filter);
* a box of another clinic answers exactly like an absent one (404, same body).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.models.box import Box

BOXES = "/api/v1/boxes"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _add_box(
    test_session,
    clinic_id: uuid.UUID,
    *,
    name: str = "Box 1",
    status: str = "active",
) -> Box:
    """Add a box outside the API (arrange helper)."""
    box = Box(clinic_id=clinic_id, name=name, status=status)
    test_session.add(box)
    await test_session.flush()
    return box


async def _count_boxes(test_session, clinic_id: uuid.UUID) -> int:
    return (
        await test_session.execute(
            select(func.count()).select_from(Box).where(Box.clinic_id == clinic_id)
        )
    ).scalar_one()


# --------------------------------------------------------------------------- #
# Create (task 2.1)
# --------------------------------------------------------------------------- #


async def test_admin_creates_a_box_in_their_own_clinic(client, seed_tenant, test_session):
    admin = await seed_tenant(role="admin", email="admin-box@example.com")

    response = await client.post(
        BOXES,
        json={"name": "Box 1"},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name", "status"}
    assert body["name"] == "Box 1"
    assert body["status"] == "active"  # default status

    created = await test_session.get(Box, uuid.UUID(body["id"]))
    assert created is not None
    assert created.clinic_id == admin.clinic.id
    assert created.name == "Box 1"
    assert created.status == "active"


@pytest.mark.parametrize("name", ["", "   "])
async def test_create_rejects_a_blank_name(client, seed_tenant, test_session, name):
    admin = await seed_tenant(role="admin", email="admin-box-name@example.com")
    before = await _count_boxes(test_session, admin.clinic.id)

    response = await client.post(
        BOXES, json={"name": name}, headers=_auth(admin.token())
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await _count_boxes(test_session, admin.clinic.id) == before


@pytest.mark.parametrize("same_clinic", [True, False])
async def test_create_rejects_a_client_supplied_clinic_id(
    client, seed_tenant, test_session, same_clinic
):
    """Spec: a payload ``clinic_id`` is a 422, whether it matches the token or not."""
    admin = await seed_tenant(role="admin", email="admin-box-clinic@example.com")
    other = await seed_tenant(role="admin", email="otra-box-clinic@example.com")
    sent = str(admin.clinic.id if same_clinic else other.clinic.id)
    before_own = await _count_boxes(test_session, admin.clinic.id)
    before_other = await _count_boxes(test_session, other.clinic.id)

    response = await client.post(
        BOXES,
        json={"name": "Box con clinica", "clinic_id": sent},
        headers=_auth(admin.token()),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert await _count_boxes(test_session, admin.clinic.id) == before_own
    assert await _count_boxes(test_session, other.clinic.id) == before_other
    assert (
        await test_session.execute(select(Box).where(Box.name == "Box con clinica"))
    ).first() is None


# --------------------------------------------------------------------------- #
# Role authorization (task 2.1 — admin-only creation)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("role", ["receptionist", "dentist"])
async def test_non_admin_roles_get_403_on_box_creation(
    client, seed_tenant, test_session, role
):
    """Non-admin roles cannot create boxes; answers 403 without side effects."""
    actor = await seed_tenant(role=role, email=f"{role}.box@example.com")
    before_boxes = await _count_boxes(test_session, actor.clinic.id)

    response = await client.post(
        BOXES,
        json={"name": "Box Prohibido"},
        headers=_auth(actor.token()),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert await _count_boxes(test_session, actor.clinic.id) == before_boxes


async def test_box_creation_requires_authentication(client):
    """Anonymous callers cannot create boxes; answers 401."""
    response = await client.post(BOXES, json={"name": "Box Anonimo"})
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


# --------------------------------------------------------------------------- #
# List / read (task 2.1)
# --------------------------------------------------------------------------- #


async def test_listing_never_includes_boxes_of_another_clinic(
    client, seed_tenant, test_session
):
    admin = await seed_tenant(role="admin", email="admin-box-list@example.com")
    own_active = await _add_box(test_session, admin.clinic.id, name="Box A1")
    own_maintenance = await _add_box(
        test_session, admin.clinic.id, name="Box A2", status="maintenance"
    )
    foreign = await seed_tenant(role="admin", email="otra-box-list@example.com")
    foreign_box = await _add_box(test_session, foreign.clinic.id, name="Box B1")

    response = await client.get(BOXES, headers=_auth(admin.token()))

    assert response.status_code == 200
    body = response.json()
    assert {row["id"] for row in body} == {
        str(own_active.id),
        str(own_maintenance.id),
    }
    # No default status filter: the spec does not restrict the listing.
    assert {row["status"] for row in body} == {"active", "maintenance"}
    assert str(foreign_box.id) not in response.text
    assert "Box B1" not in response.text


async def test_non_admin_roles_can_list_their_own_clinic(
    client, seed_tenant, test_session
):
    receptionist = await seed_tenant(
        role="receptionist", email="recepcion-box-list@example.com"
    )
    box = await _add_box(test_session, receptionist.clinic.id, name="Box Recepcion")

    response = await client.get(BOXES, headers=_auth(receptionist.token()))

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [str(box.id)]
