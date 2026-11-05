"""C-03 (`patient-management`) — schema, validation, service, and API tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, utcnow
from app.models import Clinic, Patient


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


def _clinic(**overrides: object) -> Clinic:
    values: dict[str, object] = {
        "name": "Clinica Norte",
        "slug": "clinica-norte",
        "tax_id": "30-11111111-1",
    }
    values.update(overrides)
    return Clinic(**values)


# --------------------------------------------------------------------------- #
# Task 1.1 — Patient model & schema tests
# --------------------------------------------------------------------------- #


def test_patient_table_has_expected_columns_constraints_and_indexes() -> None:
    """Task 1.1: Patient table exposes all required columns, constraints, and indexes."""
    assert "patients" in Base.metadata.tables
    patients = Base.metadata.tables["patients"]
    expected_columns = {
        "id",
        "clinic_id",
        "first_name",
        "last_name",
        "dni",
        "email",
        "phone",
        "birth_date",
        "medical_history_summary",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert expected_columns <= {c.name for c in patients.columns}
    assert patients.c.clinic_id.nullable is False
    assert patients.c.clinic_id.index is True
    assert patients.c.first_name.nullable is False
    assert patients.c.last_name.nullable is False
    assert patients.c.dni.nullable is False
    assert patients.c.email.nullable is True
    assert patients.c.phone.nullable is True
    assert patients.c.birth_date.nullable is True
    assert patients.c.medical_history_summary.nullable is True
    assert patients.c.is_active.nullable is False

    # Foreign key to clinics.id with CASCADE
    fks = list(patients.c.clinic_id.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "clinics.id"
    assert fks[0].ondelete == "CASCADE"

    # UniqueConstraint("clinic_id", "dni") -> uq_patients_clinic_id
    uq_constraints = [
        c for c in patients.constraints if isinstance(c, UniqueConstraint)
    ]
    assert any(
        [col.name for col in c.columns] == ["clinic_id", "dni"]
        and c.name == "uq_patients_clinic_id"
        for c in uq_constraints
    )

    # Composite index (clinic_id, last_name, first_name) + ix_patients_clinic_id
    index_columns = {
        idx.name: [col.name for col in idx.columns]
        for idx in patients.indexes
        if isinstance(idx, Index)
    }
    assert index_columns.get("ix_patients_clinic_id") == ["clinic_id"]
    assert index_columns.get("ix_patients_clinic_id_last_name_first_name") == [
        "clinic_id",
        "last_name",
        "first_name",
    ]


async def test_patient_persists_with_defaults_and_json_summary(
    schema_session: AsyncSession,
) -> None:
    """Task 1.1: Patient persists UTC timestamps, is_active=True, and JSON summary."""
    clinic = _clinic()
    schema_session.add(clinic)
    await schema_session.flush()

    patient = Patient(
        clinic_id=clinic.id,
        first_name="Lucia",
        last_name="Gomez",
        dni="30111222",
        email="  Lucia.Gomez@Example.COM ",
        phone="+54 9 11 5555-0000",
        birth_date=date(1990, 5, 14),
        medical_history_summary={"allergies": ["penicilina"], "smoker": False},
    )
    schema_session.add(patient)
    await schema_session.flush()

    assert patient.id is not None
    assert patient.is_active is True
    assert patient.email == "lucia.gomez@example.com"
    assert patient.medical_history_summary == {
        "allergies": ["penicilina"],
        "smoker": False,
    }
    assert isinstance(patient.created_at, datetime)
    assert patient.created_at.tzinfo is UTC
    assert patient.updated_at >= patient.created_at
    assert utcnow().tzinfo is UTC


async def test_patient_unique_constraint_is_scoped_per_clinic(
    schema_session: AsyncSession,
) -> None:
    """Task 1.1 (triangulation): same DNI in same clinic fails; same DNI in different clinic succeeds."""
    clinic_a = _clinic(slug="clinica-a", tax_id="30-11111111-1")
    clinic_b = _clinic(name="Clinica Sur", slug="clinica-b", tax_id="30-22222222-2")
    schema_session.add_all([clinic_a, clinic_b])
    await schema_session.flush()

    schema_session.add(
        Patient(
            clinic_id=clinic_a.id,
            first_name="Juan",
            last_name="Perez",
            dni="25999888",
        )
    )
    await schema_session.flush()

    # Same DNI in another clinic is allowed
    other_clinic_patient = Patient(
        clinic_id=clinic_b.id,
        first_name="Juan",
        last_name="Perez",
        dni="25999888",
    )
    schema_session.add(other_clinic_patient)
    await schema_session.flush()
    assert other_clinic_patient.id is not None

    # Duplicate DNI in the same clinic violates uq_patients_clinic_id
    schema_session.add(
        Patient(
            clinic_id=clinic_a.id,
            first_name="Otro",
            last_name="Paciente",
            dni="25999888",
        )
    )
    with pytest.raises(IntegrityError):
        await schema_session.flush()


# --------------------------------------------------------------------------- #
# Task 2.1 — Domain errors & Pydantic schemas for patients
# --------------------------------------------------------------------------- #


def test_patient_domain_errors_map_to_expected_status_and_codes() -> None:
    """Task 2.1: DuplicateDni is 409/duplicate_dni; PatientNotFound matches TenantViolation (404/not_found)."""
    from app.core.errors import DuplicateDni, PatientNotFound, TenantViolation

    dup = DuplicateDni()
    not_found = PatientNotFound()
    tenant = TenantViolation()

    assert dup.status_code == 409
    assert dup.code == "duplicate_dni"
    assert isinstance(dup.detail, str) and dup.detail

    assert not_found.status_code == 404
    assert not_found.code == "not_found"
    assert not_found.status_code == tenant.status_code
    assert not_found.code == tenant.code
    assert not_found.detail == tenant.detail == "resource not found"


def test_patient_create_schema_normalizes_dni_names_and_email() -> None:
    """Task 2.1: PatientCreate normalizes DNI (removes dots/spaces) and lowercases email."""
    from app.schemas.patients import PatientCreate

    payload = PatientCreate(
        first_name="  Lucia  ",
        last_name="  Gomez  ",
        dni=" 30.111.222 ",
        email="  LUCIA@Example.COM ",
        phone="  +54 9 11 4444-5555  ",
        birth_date=date(1992, 4, 10),
        medical_history_summary={"allergies": ["ibuprofeno"]},
    )

    assert payload.first_name == "Lucia"
    assert payload.last_name == "Gomez"
    assert payload.dni == "30111222"
    assert payload.email == "lucia@example.com"
    assert payload.phone == "+54 9 11 4444-5555"
    assert payload.birth_date == date(1992, 4, 10)
    assert payload.medical_history_summary == {"allergies": ["ibuprofeno"]}


@pytest.mark.parametrize(
    "invalid_kwargs",
    [
        {"clinic_id": "00000000-0000-0000-0000-000000000001"},
        {"dni": "   "},
        {"dni": "..."},
        {"first_name": "   "},
        {"last_name": "   "},
        {"birth_date": date(2999, 1, 1)},
        {"medical_history_summary": ["not", "an", "object"]},
        {"medical_history_summary": "string-not-dict"},
        {"email": "not-an-email"},
    ],
)
def test_patient_create_schema_rejects_invalid_fields(
    invalid_kwargs: dict[str, object],
) -> None:
    """Task 2.1 (triangulation): injected clinic_id, blank dni, future birth_date, and non-object summary fail validation."""
    from pydantic import ValidationError

    from app.schemas.patients import PatientCreate

    base: dict[str, object] = {
        "first_name": "Ana",
        "last_name": "Lopez",
        "dni": "30111222",
    }
    base.update(invalid_kwargs)
    with pytest.raises(ValidationError):
        PatientCreate(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "invalid_update",
    [
        {"clinic_id": "00000000-0000-0000-0000-000000000001"},
        {"dni": "   "},
        {"birth_date": date(2999, 12, 31)},
        {"medical_history_summary": ["list-not-dict"]},
    ],
)
def test_patient_update_schema_rejects_injected_clinic_id_and_invalid_fields(
    invalid_update: dict[str, object],
) -> None:
    """Task 2.1: PatientUpdate rejects injected clinic_id, blank dni, future birth_date, and non-dict summary."""
    from pydantic import ValidationError

    from app.schemas.patients import PatientUpdate

    with pytest.raises(ValidationError):
        PatientUpdate(**invalid_update)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Task 3.1 — Patient domain service (`app/services/patients.py`)
# --------------------------------------------------------------------------- #


def _to_principal(tenant):
    from app.services.principal import Principal

    return Principal(
        user_id=tenant.user.id,
        clinic_id=tenant.clinic.id,
        role=tenant.user.role,
        user=tenant.user,
        clinic=tenant.clinic,
    )


async def test_patient_service_creates_lists_gets_and_updates_within_clinic(
    seed_tenant, test_session
):
    """Task 3.1: create_patient, list_patients, get_patient, and update_patient work within the caller's clinic."""
    from app.core.errors import DuplicateDni, PatientNotFound
    from app.schemas.patients import PatientCreate, PatientUpdate
    from app.services import patients as patients_service

    own = await seed_tenant()
    foreign = await seed_tenant()
    own_principal = _to_principal(own)
    foreign_principal = _to_principal(foreign)

    created = await patients_service.create_patient(
        test_session,
        own_principal,
        PatientCreate(
            first_name="Sofia",
            last_name="Martinez",
            dni="33.444.555",
            email="Sofia@Example.com",
            medical_history_summary={"allergies": ["latex"]},
        ),
    )
    assert created.clinic_id == own.clinic.id
    assert created.dni == "33444555"
    assert created.email == "sofia@example.com"
    assert created.is_active is True

    # Same DNI in same clinic raises DuplicateDni
    with pytest.raises(DuplicateDni):
        await patients_service.create_patient(
            test_session,
            own_principal,
            PatientCreate(first_name="Otra", last_name="Persona", dni="33444555"),
        )

    # Same DNI in another clinic succeeds
    foreign_created = await patients_service.create_patient(
        test_session,
        foreign_principal,
        PatientCreate(first_name="Sofia", last_name="Martinez", dni="33444555"),
    )
    assert foreign_created.clinic_id == foreign.clinic.id

    # Get own vs foreign
    fetched = await patients_service.get_patient(
        test_session, own_principal, created.id
    )
    assert fetched.id == created.id
    with pytest.raises(PatientNotFound):
        await patients_service.get_patient(
            test_session, own_principal, foreign_created.id
        )

    # Update partial fields and medical_history_summary
    updated = await patients_service.update_patient(
        test_session,
        own_principal,
        created.id,
        PatientUpdate(
            phone="+54 11 9999-8888",
            medical_history_summary={"allergies": ["latex", "penicilina"]},
            is_active=False,
        ),
    )
    assert updated.phone == "+54 11 9999-8888"
    assert updated.medical_history_summary == {"allergies": ["latex", "penicilina"]}
    assert updated.is_active is False

    # Listing excludes inactive by default, includes with include_inactive=True
    assert (
        await patients_service.list_patients(test_session, own_principal)
        == []
    )
    all_own = await patients_service.list_patients(
        test_session, own_principal, include_inactive=True
    )
    assert [p.id for p in all_own] == [created.id]


# --------------------------------------------------------------------------- #
# Task 3.2 — REST endpoints (`/api/v1/patients`) integration tests
# --------------------------------------------------------------------------- #

PATIENTS = "/api/v1/patients"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("role", ["admin", "receptionist", "dentist"])
async def test_api_staff_roles_can_register_patient_in_their_clinic(
    client, seed_tenant, role: str
):
    """Task 3.2: admin, receptionist, and dentist can register a patient (201) scoped to their clinic."""
    staff = await seed_tenant(role=role)

    response = await client.post(
        PATIENTS,
        json={
            "first_name": "Valeria",
            "last_name": "Acosta",
            "dni": " 34.555.666 ",
            "email": "Valeria.Acosta@Example.com",
            "phone": "+54 9 11 1111-2222",
            "birth_date": "1988-11-20",
            "medical_history_summary": {"allergies": ["aspirina"], "diabetic": False},
        },
        headers=_auth(staff.token()),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["clinic_id"] == str(staff.clinic.id)
    assert body["first_name"] == "Valeria"
    assert body["last_name"] == "Acosta"
    assert body["dni"] == "34555666"
    assert body["email"] == "valeria.acosta@example.com"
    assert body["phone"] == "+54 9 11 1111-2222"
    assert body["birth_date"] == "1988-11-20"
    assert body["medical_history_summary"] == {
        "allergies": ["aspirina"],
        "diabetic": False,
    }
    assert body["is_active"] is True
    assert "created_at" in body and "updated_at" in body


async def test_api_duplicate_dni_in_same_clinic_returns_409_while_other_clinic_returns_201(
    client, seed_tenant
):
    """Task 3.2 (triangulation): duplicate DNI in same clinic -> 409 duplicate_dni; same DNI in other clinic -> 201."""
    clinic_a = await seed_tenant(role="receptionist")
    clinic_b = await seed_tenant(role="dentist")

    first = await client.post(
        PATIENTS,
        json={"first_name": "Diego", "last_name": "Torres", "dni": "29.888.777"},
        headers=_auth(clinic_a.token()),
    )
    assert first.status_code == 201

    duplicate = await client.post(
        PATIENTS,
        json={"first_name": "Otro", "last_name": "Nombre", "dni": "29888777"},
        headers=_auth(clinic_a.token()),
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "a patient with that DNI already exists in this clinic",
        "code": "duplicate_dni",
    }

    # Same DNI in clinic B succeeds without conflict or cross-tenant disclosure
    other_clinic = await client.post(
        PATIENTS,
        json={"first_name": "Diego", "last_name": "Torres", "dni": "29888777"},
        headers=_auth(clinic_b.token()),
    )
    assert other_clinic.status_code == 201
    assert other_clinic.json()["clinic_id"] == str(clinic_b.clinic.id)
    assert str(clinic_a.clinic.id) not in other_clinic.text


async def test_api_search_partial_update_and_logical_deactivation(
    client, seed_tenant
):
    """Task 3.2: GET /api/v1/patients searches by q, GET /{id} retrieves detail, PATCH /{id} updates & deactivates."""
    staff = await seed_tenant(role="dentist")

    p1 = (
        await client.post(
            PATIENTS,
            json={"first_name": "Carla", "last_name": "Benitez", "dni": "31111222"},
            headers=_auth(staff.token()),
        )
    ).json()
    p2 = (
        await client.post(
            PATIENTS,
            json={"first_name": "Mateo", "last_name": "Alonso", "dni": "38999000"},
            headers=_auth(staff.token()),
        )
    ).json()

    # Search by dni, first_name, last_name
    by_dni = await client.get(f"{PATIENTS}?q=38999", headers=_auth(staff.token()))
    assert by_dni.status_code == 200
    assert [row["id"] for row in by_dni.json()] == [p2["id"]]

    by_first = await client.get(f"{PATIENTS}?q=carla", headers=_auth(staff.token()))
    assert [row["id"] for row in by_first.json()] == [p1["id"]]

    by_last = await client.get(f"{PATIENTS}?q=ALONSO", headers=_auth(staff.token()))
    assert [row["id"] for row in by_last.json()] == [p2["id"]]

    # Detail retrieval
    detail = await client.get(f"{PATIENTS}/{p1['id']}", headers=_auth(staff.token()))
    assert detail.status_code == 200
    assert detail.json()["id"] == p1["id"]

    # Partial update + logical deactivation
    patched = await client.patch(
        f"{PATIENTS}/{p1['id']}",
        json={
            "phone": "+54 11 2222-3333",
            "medical_history_summary": {"conditions": ["hipertension"]},
            "is_active": False,
        },
        headers=_auth(staff.token()),
    )
    assert patched.status_code == 200
    patched_body = patched.json()
    assert patched_body["phone"] == "+54 11 2222-3333"
    assert patched_body["medical_history_summary"] == {"conditions": ["hipertension"]}
    assert patched_body["is_active"] is False

    # Excluded from default active listing, included when include_inactive=true
    active_list = await client.get(PATIENTS, headers=_auth(staff.token()))
    assert [row["id"] for row in active_list.json()] == [p2["id"]]

    with_inactive = await client.get(
        f"{PATIENTS}?include_inactive=true", headers=_auth(staff.token())
    )
    assert {row["id"] for row in with_inactive.json()} == {p1["id"], p2["id"]}


async def test_api_patients_rejects_unauthenticated_and_inactive_clinic(
    client, seed_tenant
):
    """Task 3.2: unauthenticated requests get 401; inactive clinic gets 403."""
    pid = uuid.uuid4()
    for response in (
        await client.post(
            PATIENTS,
            json={"first_name": "Sin", "last_name": "Token", "dni": "30000111"},
        ),
        await client.get(PATIENTS),
        await client.get(f"{PATIENTS}/{pid}"),
        await client.patch(f"{PATIENTS}/{pid}", json={"first_name": "Nada"}),
    ):
        assert response.status_code == 401
        assert response.json()["code"] == "authentication_failed"

    inactive_tenant = await seed_tenant(role="admin", clinic_active=False)
    forbidden = await client.get(PATIENTS, headers=_auth(inactive_tenant.token()))
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"


# --------------------------------------------------------------------------- #
# Task 3.3 — Multi-tenant isolation & health data privacy (Ley 25.326)
# --------------------------------------------------------------------------- #


async def test_cross_tenant_get_and_patch_return_indistinguishable_404_and_do_not_mutate(
    client, seed_tenant, test_session
):
    """Task 3.3: GET and PATCH on a patient from another clinic return 404 identical to a non-existent UUID and modify nothing."""
    clinic_a = await seed_tenant(role="admin")
    clinic_b = await seed_tenant(role="dentist")

    created_in_b = (
        await client.post(
            PATIENTS,
            json={
                "first_name": "Elena",
                "last_name": "Peralta",
                "dni": "27654321",
                "medical_history_summary": {"allergies": ["iodine"]},
            },
            headers=_auth(clinic_b.token()),
        )
    ).json()
    foreign_id = created_in_b["id"]
    absent_id = str(uuid.uuid4())

    # GET cross-tenant vs absent
    foreign_get = await client.get(
        f"{PATIENTS}/{foreign_id}", headers=_auth(clinic_a.token())
    )
    absent_get = await client.get(
        f"{PATIENTS}/{absent_id}", headers=_auth(clinic_a.token())
    )
    assert foreign_get.status_code == absent_get.status_code == 404
    assert foreign_get.json() == absent_get.json() == {
        "detail": "resource not found",
        "code": "not_found",
    }

    # PATCH cross-tenant vs absent
    foreign_patch = await client.patch(
        f"{PATIENTS}/{foreign_id}",
        json={
            "first_name": "Intruso",
            "medical_history_summary": {"allergies": ["hacked"]},
            "is_active": False,
        },
        headers=_auth(clinic_a.token()),
    )
    absent_patch = await client.patch(
        f"{PATIENTS}/{absent_id}",
        json={"first_name": "Intruso"},
        headers=_auth(clinic_a.token()),
    )
    assert foreign_patch.status_code == absent_patch.status_code == 404
    assert foreign_patch.json() == absent_patch.json() == {
        "detail": "resource not found",
        "code": "not_found",
    }

    # Listing from clinic A never includes clinic B's patient
    list_a = await client.get(
        f"{PATIENTS}?include_inactive=true", headers=_auth(clinic_a.token())
    )
    assert list_a.json() == []

    # Verify clinic B's patient was not mutated
    intact = await client.get(
        f"{PATIENTS}/{foreign_id}", headers=_auth(clinic_b.token())
    )
    assert intact.status_code == 200
    assert intact.json()["first_name"] == "Elena"
    assert intact.json()["medical_history_summary"] == {"allergies": ["iodine"]}
    assert intact.json()["is_active"] is True


async def test_patient_operations_and_errors_never_leak_sql_or_pii_to_logs_or_responses(
    client, seed_tenant, caplog
):
    """Task 3.3 (triangulation): no patient PII or medical_history_summary is written to logs or error bodies (Ley 25.326)."""
    import logging

    caplog.set_level(logging.DEBUG)
    staff = await seed_tenant(role="receptionist")

    sensitive_dni = "39876543"
    sensitive_condition = "vih_positivo_confidencial_ley_25326"
    sensitive_email = "privado.paciente@example.com"

    created = await client.post(
        PATIENTS,
        json={
            "first_name": "PacientePrivado",
            "last_name": "ApellidoSecreto",
            "dni": sensitive_dni,
            "email": sensitive_email,
            "medical_history_summary": {"confidential_note": sensitive_condition},
        },
        headers=_auth(staff.token()),
    )
    assert created.status_code == 201

    # Trigger 409 duplicate_dni and 422 validation_error
    conflict = await client.post(
        PATIENTS,
        json={
            "first_name": "PacientePrivado",
            "last_name": "ApellidoSecreto",
            "dni": sensitive_dni,
            "medical_history_summary": {"confidential_note": sensitive_condition},
        },
        headers=_auth(staff.token()),
    )
    assert conflict.status_code == 409

    invalid = await client.post(
        PATIENTS,
        json={
            "first_name": "PacientePrivado",
            "last_name": "ApellidoSecreto",
            "dni": sensitive_dni,
            "clinic_id": str(uuid.uuid4()),
            "medical_history_summary": {"confidential_note": sensitive_condition},
        },
        headers=_auth(staff.token()),
    )
    assert invalid.status_code == 422

    # Error bodies must never contain SQL, driver messages, or patient PII / medical history
    for err_resp in (conflict, invalid):
        assert set(err_resp.json()) == {"detail", "code"}
        for forbidden in (
            sensitive_dni,
            sensitive_condition,
            sensitive_email,
            "PacientePrivado",
            "ApellidoSecreto",
            "SELECT",
            "INSERT",
            "uq_patients_clinic_id",
        ):
            assert forbidden not in err_resp.text

    # Application logs must not contain sensitive health data or patient PII
    app_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if not record.name.startswith(("sqlalchemy", "aiosqlite", "httpcore", "httpx"))
    )
    for secret in (
        sensitive_dni,
        sensitive_condition,
        sensitive_email,
        "PacientePrivado",
        "ApellidoSecreto",
    ):
        assert secret not in app_logs


# --------------------------------------------------------------------------- #
# Task 3.4 — API documentation contract verification (`backend/docs/api-patients.md`)
# --------------------------------------------------------------------------- #


def test_api_patients_documentation_exists_and_matches_contract():
    """Task 3.4: backend/docs/api-patients.md documents all endpoints, query params, medical_history_summary, and error codes."""
    from pathlib import Path

    doc_path = Path(__file__).resolve().parents[1] / "docs" / "api-patients.md"
    assert doc_path.exists(), "backend/docs/api-patients.md must exist"
    text = doc_path.read_text(encoding="utf-8")

    for required in (
        "POST /api/v1/patients",
        "GET /api/v1/patients",
        "GET /api/v1/patients/{id}",
        "PATCH /api/v1/patients/{id}",
        "include_inactive",
        "limit",
        "offset",
        "medical_history_summary",
        "duplicate_dni",
        "not_found",
        "validation_error",
        "authentication_failed",
        "forbidden",
        "Ley 25.326",
    ):
        assert required in text, f"Missing '{required}' in api-patients.md"
