"""Clinic-scoped patient administration router: ``/api/v1/patients`` (D4/D5).

All endpoints require an authenticated clinic staff member
(``admin``, ``receptionist``, or ``dentist``) and automatically scope reads and
writes to ``principal.clinic_id``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.patients import PatientCreate, PatientResponse, PatientUpdate
from app.services import patients as patients_service
from app.services.principal import Principal

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

StaffGuard = Annotated[
    Principal, Depends(require_roles("admin", "receptionist", "dentist"))
]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    payload: PatientCreate,
    principal: StaffGuard,
    db: DbSession,
) -> PatientResponse:
    """Register a patient inside the caller's active clinic."""
    patient = await patients_service.create_patient(db, principal, payload)
    await db.commit()
    return PatientResponse.model_validate(patient)


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    principal: StaffGuard,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=120)] = None,
    include_inactive: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PatientResponse]:
    """List or search patients belonging to the caller's active clinic."""
    patients = await patients_service.list_patients(
        db,
        principal,
        q=q,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return [PatientResponse.model_validate(patient) for patient in patients]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    principal: StaffGuard,
    db: DbSession,
) -> PatientResponse:
    """Retrieve a single patient belonging to the caller's active clinic."""
    patient = await patients_service.get_patient(db, principal, patient_id)
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    principal: StaffGuard,
    db: DbSession,
) -> PatientResponse:
    """Partially update a patient's personal data, anamnesis summary, or active state."""
    patient = await patients_service.update_patient(
        db, principal, patient_id, payload
    )
    await db.commit()
    return PatientResponse.model_validate(patient)
