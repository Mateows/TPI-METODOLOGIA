"""Persistence layer (design D13).

Every SQLAlchemy query or write lives here; services and the CLI only
orchestrate business rules. Repositories ``flush`` but never ``commit``: the
transaction boundary stays in the router (or in the service for the revocation
paths that must survive an error response, design D3). Clinic-scoped reads take
``clinic_id`` explicitly (design D5); global lookups are named as such.
"""

from __future__ import annotations

from app.repositories.appointments import AppointmentRepository
from app.repositories.base import ClinicScope, TenantScopedRepository
from app.repositories.clinics import ClinicRepository
from app.repositories.patients import PatientRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository

__all__ = [
    "AppointmentRepository",
    "ClinicRepository",
    "ClinicScope",
    "PatientRepository",
    "RefreshTokenRepository",
    "TenantScopedRepository",
    "UserRepository",
]
