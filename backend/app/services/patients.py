"""Clinic-scoped patient administration service (design D1/D2/D3/D5/D6).

Every query and write is delegated to ``PatientRepository`` (D13, Rule 4).
No patient PII or ``medical_history_summary`` is ever logged (Ley 25.326).
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import DuplicateDni, PatientNotFound
from app.models.patient import Patient
from app.repositories.patients import PatientRepository
from app.schemas.patients import PatientCreate, PatientUpdate
from app.services.principal import Principal


async def create_patient(
    db: AsyncSession, principal: Principal, payload: PatientCreate
) -> Patient:
    """Register a patient inside ``principal.clinic_id``."""
    repo = PatientRepository(db, principal)
    if await repo.dni_exists(payload.dni):
        raise DuplicateDni()

    patient = Patient(
        clinic_id=principal.clinic_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        dni=payload.dni,
        email=payload.email,
        phone=payload.phone,
        birth_date=payload.birth_date,
        medical_history_summary=payload.medical_history_summary,
        is_active=True,
    )
    try:
        await repo.add(patient)
    except IntegrityError as exc:
        raise DuplicateDni() from exc
    return patient


async def list_patients(
    db: AsyncSession,
    principal: Principal,
    *,
    q: str | None = None,
    include_inactive: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Patient]:
    """List or search patients belonging to ``principal.clinic_id``."""
    repo = PatientRepository(db, principal)
    rows = await repo.search(
        q, include_inactive=include_inactive, limit=limit, offset=offset
    )
    return list(rows)


async def get_patient(
    db: AsyncSession, principal: Principal, patient_id: uuid.UUID
) -> Patient:
    """Retrieve a patient in ``principal.clinic_id`` or raise ``PatientNotFound`` (404)."""
    repo = PatientRepository(db, principal)
    patient = await repo.get(patient_id)
    if patient is None:
        raise PatientNotFound()
    return patient


async def update_patient(
    db: AsyncSession,
    principal: Principal,
    patient_id: uuid.UUID,
    payload: PatientUpdate,
) -> Patient:
    """Partially update a patient belonging to ``principal.clinic_id``."""
    repo = PatientRepository(db, principal)
    patient = await repo.get(patient_id)
    if patient is None:
        raise PatientNotFound()

    updates = payload.model_dump(exclude_unset=True)
    new_dni = updates.get("dni")
    if new_dni is not None and new_dni != patient.dni:
        if await repo.dni_exists(new_dni, exclude_id=patient.id):
            raise DuplicateDni()

    for field_name, value in updates.items():
        setattr(patient, field_name, value)
    if updates:
        patient.updated_at = utcnow()

    try:
        await repo.save(patient)
    except IntegrityError as exc:
        raise DuplicateDni() from exc
    return patient
