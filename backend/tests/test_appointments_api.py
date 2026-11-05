"""C-04 — appointments slice API integration tests (spec: appointment-agenda).

Covers all spec requirements and scenarios:
1. Agenda clinic scope is server-derived (rejects payload clinic_id, scopes to session).
2. Appointment creation (happy path, timezone-aware, UTC normalization).
3. Invalid time range rejected with semantic error.
4. Naive datetimes rejected with 422 validation_error.
5. Overlap prevention (dentist, box, contained, exact, contiguous allowed, cancelled excluded).
6. Cross-clinic reference isolation (patient, dentist, box of other clinic -> 404).
7. Appointment state machine and transition matrix (valid transitions, invalid -> 409, unknown -> 422).
8. Read isolation (listing filtered by clinic and date range, cross-clinic GET/PATCH -> 404).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.appointment import Appointment
from app.models.box import Box
from app.models.patient import Patient
from app.models.user import User

APPOINTMENTS = "/api/v1/appointments"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_agenda_fixtures(test_session, clinic_id: uuid.UUID):
    """Seed patient, dentist user, and box for a clinic."""
    patient = Patient(
        clinic_id=clinic_id,
        first_name="Carlos",
        last_name="Perez",
        dni=f"dni-{uuid.uuid4().hex[:8]}",
    )
    dentist = User(
        clinic_id=clinic_id,
        email=f"dentist-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$" + "x" * 53,
        full_name="Dr. Gomez",
        role="dentist",
        is_active=True,
    )
    box = Box(clinic_id=clinic_id, name=f"Box-{uuid.uuid4().hex[:6]}", status="active")
    test_session.add_all([patient, dentist, box])
    await test_session.flush()
    return patient, dentist, box


# --------------------------------------------------------------------------- #
# 1. Clinic scope is server-derived
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("same_clinic", [True, False])
async def test_create_rejects_payload_with_clinic_id(
    client, seed_tenant, test_session, same_clinic
):
    """Spec: payload cannot set clinic_id; rejected with 422 validation_error."""
    tenant = await seed_tenant(role="receptionist")
    other = await seed_tenant(role="admin")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    clinic_to_send = str(tenant.clinic.id if same_clinic else other.clinic.id)
    payload = {
        "clinic_id": clinic_to_send,
        "patient_id": str(p.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
    }
    response = await client.post(
        APPOINTMENTS, json=payload, headers=_auth(tenant.token())
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# --------------------------------------------------------------------------- #
# 2. Appointment creation happy path & UTC normalization
# --------------------------------------------------------------------------- #


async def test_create_valid_appointment_and_persists_in_authenticated_clinic(
    client, seed_tenant, test_session
):
    """Spec: valid appointment created in scheduled status, clinic-owned, UTC normalized."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    payload = {
        "patient_id": str(p.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
        "notes": "Consulta general",
    }
    response = await client.post(
        APPOINTMENTS, json=payload, headers=_auth(tenant.token())
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["patient_id"] == str(p.id)
    assert body["dentist_id"] == str(d.id)
    assert body["box_id"] == str(b.id)
    assert body["notes"] == "Consulta general"

    # Verify persisted in database
    appt_id = uuid.UUID(body["id"])
    persisted = await test_session.get(Appointment, appt_id)
    assert persisted is not None
    assert persisted.clinic_id == tenant.clinic.id
    assert persisted.status == "scheduled"


async def test_create_normalizes_timezone_offset_to_utc(
    client, seed_tenant, test_session
):
    """Spec: offset datetime (-03:00) is normalized to UTC instant."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    # 13:00 -03:00 is 16:00 UTC
    payload = {
        "patient_id": str(p.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": "2026-11-10T13:00:00-03:00",
        "end_time": "2026-11-10T13:30:00-03:00",
    }
    response = await client.post(
        APPOINTMENTS, json=payload, headers=_auth(tenant.token())
    )
    assert response.status_code == 201
    body = response.json()

    # Returned datetime must correspond to 16:00:00 UTC
    start_dt = datetime.fromisoformat(body["start_time"].replace("Z", "+00:00"))
    assert start_dt == datetime(2026, 11, 10, 16, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# 3. Validation errors: invalid time range & naive datetimes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("start_str", "end_str"),
    [
        ("2026-11-10T10:30:00Z", "2026-11-10T10:00:00Z"),  # end before start
        ("2026-11-10T10:00:00Z", "2026-11-10T10:00:00Z"),  # equal start and end
    ],
)
async def test_create_rejects_invalid_time_range(
    client, seed_tenant, test_session, start_str, end_str
):
    """Spec: end_time <= start_time rejected with semantic business error."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    payload = {
        "patient_id": str(p.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": start_str,
        "end_time": end_str,
    }
    response = await client.post(
        APPOINTMENTS, json=payload, headers=_auth(tenant.token())
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_time_range"


@pytest.mark.parametrize(
    ("start_str", "end_str"),
    [
        ("2026-11-10T10:00:00", "2026-11-10T10:30:00Z"),   # start naive
        ("2026-11-10T10:00:00Z", "2026-11-10T10:30:00"),   # end naive
        ("2026-11-10T10:00:00", "2026-11-10T10:30:00"),    # both naive
    ],
)
async def test_create_rejects_naive_datetime(
    client, seed_tenant, test_session, start_str, end_str
):
    """Spec: naive datetime rejected with 422 validation_error."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    payload = {
        "patient_id": str(p.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": start_str,
        "end_time": end_str,
    }
    response = await client.post(
        APPOINTMENTS, json=payload, headers=_auth(tenant.token())
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# --------------------------------------------------------------------------- #
# 4. Cross-clinic reference isolation
# --------------------------------------------------------------------------- #


async def test_create_rejects_foreign_patient(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    other = await seed_tenant(role="admin")
    p_own, d_own, b_own = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    p_foreign, _, _ = await _seed_agenda_fixtures(test_session, other.clinic.id)

    payload = {
        "patient_id": str(p_foreign.id),
        "dentist_id": str(d_own.id),
        "box_id": str(b_own.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
    }
    response = await client.post(APPOINTMENTS, json=payload, headers=_auth(tenant.token()))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_rejects_foreign_dentist(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    other = await seed_tenant(role="admin")
    p_own, d_own, b_own = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    _, d_foreign, _ = await _seed_agenda_fixtures(test_session, other.clinic.id)

    payload = {
        "patient_id": str(p_own.id),
        "dentist_id": str(d_foreign.id),
        "box_id": str(b_own.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
    }
    response = await client.post(APPOINTMENTS, json=payload, headers=_auth(tenant.token()))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_rejects_foreign_box(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    other = await seed_tenant(role="admin")
    p_own, d_own, b_own = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    _, _, b_foreign = await _seed_agenda_fixtures(test_session, other.clinic.id)

    payload = {
        "patient_id": str(p_own.id),
        "dentist_id": str(d_own.id),
        "box_id": str(b_foreign.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
    }
    response = await client.post(APPOINTMENTS, json=payload, headers=_auth(tenant.token()))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_rejects_user_who_is_not_a_dentist(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    p, _, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    receptionist_user = User(
        clinic_id=tenant.clinic.id,
        email="receptionist-only@example.com",
        password_hash="$2b$12$" + "x" * 53,
        full_name="Recep",
        role="receptionist",
        is_active=True,
    )
    test_session.add(receptionist_user)
    await test_session.flush()

    payload = {
        "patient_id": str(p.id),
        "dentist_id": str(receptionist_user.id),
        "box_id": str(b.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T10:30:00Z",
    }
    response = await client.post(APPOINTMENTS, json=payload, headers=_auth(tenant.token()))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


# --------------------------------------------------------------------------- #
# 5. Overlap prevention (RN-01)
# --------------------------------------------------------------------------- #


async def test_overlap_prevention_scenarios(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    p1, dentist1, box1 = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    p2, dentist2, box2 = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    # Base appointment: 10:00 to 11:00
    base_payload = {
        "patient_id": str(p1.id),
        "dentist_id": str(dentist1.id),
        "box_id": str(box1.id),
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T11:00:00Z",
    }
    res_base = await client.post(APPOINTMENTS, json=base_payload, headers=_auth(tenant.token()))
    assert res_base.status_code == 201

    # (a) Dentist overlap (10:30 - 11:30, different box)
    res_dentist = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist1.id),
            "box_id": str(box2.id),
            "start_time": "2026-11-10T10:30:00Z",
            "end_time": "2026-11-10T11:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_dentist.status_code == 409
    assert res_dentist.json()["code"] == "appointment_overlap"

    # (b) Box overlap (10:30 - 11:30, different dentist)
    res_box = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist2.id),
            "box_id": str(box1.id),
            "start_time": "2026-11-10T10:30:00Z",
            "end_time": "2026-11-10T11:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_box.status_code == 409
    assert res_box.json()["code"] == "appointment_overlap"

    # (c) Contained appointment (10:15 - 10:45)
    res_contained = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist1.id),
            "box_id": str(box1.id),
            "start_time": "2026-11-10T10:15:00Z",
            "end_time": "2026-11-10T10:45:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_contained.status_code == 409
    assert res_contained.json()["code"] == "appointment_overlap"

    # (d) Exact match (10:00 - 11:00)
    res_exact = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist1.id),
            "box_id": str(box1.id),
            "start_time": "2026-11-10T10:00:00Z",
            "end_time": "2026-11-10T11:00:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_exact.status_code == 409
    assert res_exact.json()["code"] == "appointment_overlap"

    # (e) Consecutive intervals allowed: 09:00 - 10:00 and 11:00 - 12:00
    res_before = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist1.id),
            "box_id": str(box1.id),
            "start_time": "2026-11-10T09:00:00Z",
            "end_time": "2026-11-10T10:00:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_before.status_code == 201

    res_after = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p2.id),
            "dentist_id": str(dentist1.id),
            "box_id": str(box1.id),
            "start_time": "2026-11-10T11:00:00Z",
            "end_time": "2026-11-10T12:00:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res_after.status_code == 201


async def test_cancelled_appointment_frees_the_interval(client, seed_tenant, test_session):
    """Spec: appointment in cancelled status does not participate in overlap detection."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    # Create appointment 15:00 - 16:00
    res = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-10T15:00:00Z",
            "end_time": "2026-11-10T16:00:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Cancel the appointment
    patch_res = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "cancelled"},
        headers=_auth(tenant.token()),
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "cancelled"

    # Now create new appointment in exact same interval
    res2 = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-10T15:00:00Z",
            "end_time": "2026-11-10T16:00:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res2.status_code == 201


# --------------------------------------------------------------------------- #
# 6. State transitions matrix
# --------------------------------------------------------------------------- #


async def test_appointment_state_transitions(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    # Create scheduled appointment
    res = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-12T10:00:00Z",
            "end_time": "2026-11-12T10:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    assert res.status_code == 201
    appt_id = res.json()["id"]

    # Invalid transition: scheduled -> attended (not declared)
    err_att = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "attended"},
        headers=_auth(tenant.token()),
    )
    assert err_att.status_code == 409
    assert err_att.json()["code"] == "invalid_appointment_transition"

    # Valid transition: scheduled -> confirmed
    conf = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "confirmed"},
        headers=_auth(tenant.token()),
    )
    assert conf.status_code == 200
    assert conf.json()["status"] == "confirmed"

    # Valid transition: confirmed -> attended
    att = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "attended"},
        headers=_auth(tenant.token()),
    )
    assert att.status_code == 200
    assert att.json()["status"] == "attended"

    # Invalid transition from attended: attended -> scheduled
    err_back = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "scheduled"},
        headers=_auth(tenant.token()),
    )
    assert err_back.status_code == 409
    assert err_back.json()["code"] == "invalid_appointment_transition"


async def test_unknown_status_is_rejected_with_validation_error(client, seed_tenant, test_session):
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    res = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-13T10:00:00Z",
            "end_time": "2026-11-13T10:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    appt_id = res.json()["id"]

    unknown = await client.patch(
        f"{APPOINTMENTS}/{appt_id}/status",
        json={"status": "flying"},
        headers=_auth(tenant.token()),
    )
    assert unknown.status_code == 422
    assert unknown.json()["code"] == "validation_error"


# --------------------------------------------------------------------------- #
# 7. Read isolation & queries
# --------------------------------------------------------------------------- #


async def test_get_and_patch_foreign_clinic_appointment_returns_404(
    client, seed_tenant, test_session
):
    tenant = await seed_tenant(role="receptionist")
    foreign = await seed_tenant(role="admin")
    p, d, b = await _seed_agenda_fixtures(test_session, foreign.clinic.id)

    # Create appointment in foreign clinic
    foreign_res = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-14T10:00:00Z",
            "end_time": "2026-11-14T10:30:00Z",
        },
        headers=_auth(foreign.token()),
    )
    assert foreign_res.status_code == 201
    foreign_id = foreign_res.json()["id"]

    # Read from tenant clinic: must return 404
    get_res = await client.get(
        f"{APPOINTMENTS}/{foreign_id}", headers=_auth(tenant.token())
    )
    assert get_res.status_code == 404
    assert get_res.json()["code"] == "not_found"

    # Patch from tenant clinic: must return 404
    patch_res = await client.patch(
        f"{APPOINTMENTS}/{foreign_id}/status",
        json={"status": "confirmed"},
        headers=_auth(tenant.token()),
    )
    assert patch_res.status_code == 404
    assert patch_res.json()["code"] == "not_found"


async def test_list_appointments_filters_by_clinic_and_date_range(
    client, seed_tenant, test_session
):
    tenant = await seed_tenant(role="receptionist")
    foreign = await seed_tenant(role="admin")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    fp, fd, fb = await _seed_agenda_fixtures(test_session, foreign.clinic.id)

    # Day 1 appt in tenant clinic
    res1 = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-15T09:00:00Z",
            "end_time": "2026-11-15T09:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    # Day 2 appt in tenant clinic
    res2 = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-16T09:00:00Z",
            "end_time": "2026-11-16T09:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    # Day 1 appt in foreign clinic
    await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(fp.id),
            "dentist_id": str(fd.id),
            "box_id": str(fb.id),
            "start_time": "2026-11-15T09:00:00Z",
            "end_time": "2026-11-15T09:30:00Z",
        },
        headers=_auth(foreign.token()),
    )

    # List all tenant appointments
    all_res = await client.get(APPOINTMENTS, headers=_auth(tenant.token()))
    assert all_res.status_code == 200
    ids = [a["id"] for a in all_res.json()]
    assert res1.json()["id"] in ids
    assert res2.json()["id"] in ids

    # List filtered by date range for Day 1 only
    day1_res = await client.get(
        f"{APPOINTMENTS}?start_time=2026-11-15T00:00:00Z&end_time=2026-11-15T23:59:59Z",
        headers=_auth(tenant.token()),
    )
    assert day1_res.status_code == 200
    day1_ids = [a["id"] for a in day1_res.json()]
    assert day1_ids == [res1.json()["id"]]


# --------------------------------------------------------------------------- #
# 8. Triangulation: Roles, Contiguous chains, Cancellation transitions
# --------------------------------------------------------------------------- #


async def test_unauthenticated_request_is_rejected(client):
    """Anonymous callers cannot access appointments; returns 401."""
    res = await client.get(APPOINTMENTS)
    assert res.status_code == 401
    assert res.json()["code"] == "authentication_failed"


@pytest.mark.parametrize("role", ["admin", "receptionist", "dentist"])
async def test_all_staff_roles_can_create_and_read_appointments(
    client, seed_tenant, test_session, role
):
    """All clinic staff members can schedule appointments."""
    actor = await seed_tenant(role=role, email=f"{role}-staff@example.com")
    p, d, b = await _seed_agenda_fixtures(test_session, actor.clinic.id)

    res = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-20T10:00:00Z",
            "end_time": "2026-11-20T10:30:00Z",
        },
        headers=_auth(actor.token()),
    )
    assert res.status_code == 201


async def test_chained_contiguous_appointments_all_succeed(
    client, seed_tenant, test_session
):
    """Multiple contiguous appointments [10:00, 10:30), [10:30, 11:00), [11:00, 11:30) can be scheduled."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    slots = [
        ("2026-11-21T10:00:00Z", "2026-11-21T10:30:00Z"),
        ("2026-11-21T10:30:00Z", "2026-11-21T11:00:00Z"),
        ("2026-11-21T11:00:00Z", "2026-11-21T11:30:00Z"),
    ]
    for start_t, end_t in slots:
        res = await client.post(
            APPOINTMENTS,
            json={
                "patient_id": str(p.id),
                "dentist_id": str(d.id),
                "box_id": str(b.id),
                "start_time": start_t,
                "end_time": end_t,
            },
            headers=_auth(tenant.token()),
        )
        assert res.status_code == 201


async def test_cancellation_paths(client, seed_tenant, test_session):
    """Can cancel from both scheduled and confirmed; cannot transition from cancelled."""
    tenant = await seed_tenant(role="receptionist")
    p, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)

    # Path 1: scheduled -> cancelled
    res1 = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-22T10:00:00Z",
            "end_time": "2026-11-22T10:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    a1_id = res1.json()["id"]
    cancel_res1 = await client.patch(
        f"{APPOINTMENTS}/{a1_id}/status",
        json={"status": "cancelled"},
        headers=_auth(tenant.token()),
    )
    assert cancel_res1.status_code == 200
    assert cancel_res1.json()["status"] == "cancelled"

    # From cancelled -> attended must fail
    err1 = await client.patch(
        f"{APPOINTMENTS}/{a1_id}/status",
        json={"status": "attended"},
        headers=_auth(tenant.token()),
    )
    assert err1.status_code == 409
    assert err1.json()["code"] == "invalid_appointment_transition"

    # Path 2: scheduled -> confirmed -> cancelled
    res2 = await client.post(
        APPOINTMENTS,
        json={
            "patient_id": str(p.id),
            "dentist_id": str(d.id),
            "box_id": str(b.id),
            "start_time": "2026-11-22T11:00:00Z",
            "end_time": "2026-11-22T11:30:00Z",
        },
        headers=_auth(tenant.token()),
    )
    a2_id = res2.json()["id"]
    await client.patch(
        f"{APPOINTMENTS}/{a2_id}/status",
        json={"status": "confirmed"},
        headers=_auth(tenant.token()),
    )
    cancel_res2 = await client.patch(
        f"{APPOINTMENTS}/{a2_id}/status",
        json={"status": "cancelled"},
        headers=_auth(tenant.token()),
    )
    assert cancel_res2.status_code == 200
    assert cancel_res2.json()["status"] == "cancelled"


# --------------------------------------------------------------------------- #
# 9. API documentation contract verification (`backend/docs/api-agenda.md`)
# --------------------------------------------------------------------------- #


def test_api_agenda_documentation_exists_and_matches_contract():
    """Task 3.2: backend/docs/api-agenda.md documents endpoints, UTC rules, overlap rules, and error codes."""
    from pathlib import Path

    doc_path = Path(__file__).resolve().parents[1] / "docs" / "api-agenda.md"
    assert doc_path.exists(), "backend/docs/api-agenda.md must exist"
    text = doc_path.read_text(encoding="utf-8")

    for required in (
        "POST /api/v1/boxes",
        "GET /api/v1/boxes",
        "GET /api/v1/boxes/{id}",
        "POST /api/v1/appointments",
        "GET /api/v1/appointments",
        "GET /api/v1/appointments/{id}",
        "PATCH /api/v1/appointments/{id}/status",
        "RN-01",
        "RN-07",
        "appointment_overlap",
        "invalid_appointment_transition",
        "invalid_time_range",
        "validation_error",
        "authentication_failed",
        "not_found",
        "scheduled",
        "confirmed",
        "attended",
        "cancelled",
        "Ley 25.326",
    ):
        assert required in text, f"Missing '{required}' in api-agenda.md"


# --------------------------------------------------------------------------- #
# 10. Concurrency verification (task 2.4 — concurrent booking collision)
# --------------------------------------------------------------------------- #


async def test_concurrent_appointment_booking_rejects_overlap_with_409(
    client, seed_tenant, test_session
):
    """Task 2.4: two concurrent booking attempts for the same interval and dentist
    must serialize: exactly one succeeds (201) and the second is rejected with 409
    appointment_overlap, persisting exactly one record.
    """
    import asyncio

    tenant = await seed_tenant(role="receptionist")
    p1, d, b = await _seed_agenda_fixtures(test_session, tenant.clinic.id)
    p2 = Patient(
        clinic_id=tenant.clinic.id,
        first_name="Ana",
        last_name="Lopez",
        dni=f"dni-{uuid.uuid4().hex[:8]}",
    )
    test_session.add(p2)
    await test_session.flush()

    payload1 = {
        "patient_id": str(p1.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": "2026-11-20T14:00:00Z",
        "end_time": "2026-11-20T14:30:00Z",
    }
    payload2 = {
        "patient_id": str(p2.id),
        "dentist_id": str(d.id),
        "box_id": str(b.id),
        "start_time": "2026-11-20T14:00:00Z",
        "end_time": "2026-11-20T14:30:00Z",
    }

    # Execute both requests concurrently
    res1, res2 = await asyncio.gather(
        client.post(APPOINTMENTS, json=payload1, headers=_auth(tenant.token())),
        client.post(APPOINTMENTS, json=payload2, headers=_auth(tenant.token())),
    )

    statuses = [res1.status_code, res2.status_code]
    assert 201 in statuses
    assert 409 in statuses

    conflict_res = res1 if res1.status_code == 409 else res2
    assert conflict_res.json()["code"] == "appointment_overlap"

    # Exactly one appointment was persisted in the database
    res = await test_session.execute(
        select(func.count(Appointment.id)).where(Appointment.clinic_id == tenant.clinic.id)
    )
    count = res.scalar_one()
    assert count == 1
