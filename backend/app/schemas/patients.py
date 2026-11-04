"""Pydantic V2 contracts for ``/api/v1/patients`` (design D1/D2/D5).

``extra="forbid"`` rejects any client-supplied ``clinic_id``: the tenant scope
always comes from the verified ``Principal``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.database import utcnow


def _normalize_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be blank")
    return stripped


def _normalize_dni(value: str) -> str:
    cleaned = value.strip().replace(".", "").replace(" ", "")
    if not cleaned or not cleaned.isalnum():
        raise ValueError("dni must be a non-empty alphanumeric identifier")
    if len(cleaned) > 32:
        raise ValueError("dni exceeds maximum length")
    return cleaned


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    email = value.strip().lower()
    if not email:
        raise ValueError("email must not be blank")
    local, _, domain = email.partition("@")
    if not local or not domain or "@" in domain or any(c.isspace() for c in email):
        raise ValueError("invalid email address")
    return email


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("phone must not be blank")
    return stripped


def _validate_birth_date(value: date | None) -> date | None:
    if value is None:
        return None
    if value > utcnow().date():
        raise ValueError("birth_date cannot be in the future")
    return value


class PatientCreate(BaseModel):
    """Payload to register a patient inside the caller's clinic."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    dni: str = Field(min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    birth_date: date | None = None
    medical_history_summary: dict[str, Any] | None = None

    @field_validator("first_name")
    @classmethod
    def _first_name(cls, value: str) -> str:
        return _normalize_text(value, "first_name")

    @field_validator("last_name")
    @classmethod
    def _last_name(cls, value: str) -> str:
        return _normalize_text(value, "last_name")

    @field_validator("dni")
    @classmethod
    def _dni(cls, value: str) -> str:
        return _normalize_dni(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _normalize_email(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _normalize_phone(value)

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, value: date | None) -> date | None:
        return _validate_birth_date(value)


class PatientUpdate(BaseModel):
    """Partial update payload for a patient (including logical deactivation)."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    dni: str | None = Field(default=None, min_length=1, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    birth_date: date | None = None
    medical_history_summary: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("first_name")
    @classmethod
    def _first_name(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_text(value, "first_name")

    @field_validator("last_name")
    @classmethod
    def _last_name(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_text(value, "last_name")

    @field_validator("dni")
    @classmethod
    def _dni(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_dni(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return _normalize_email(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _normalize_phone(value)

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, value: date | None) -> date | None:
        return _validate_birth_date(value)


class PatientResponse(BaseModel):
    """API representation of a clinic-scoped patient."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    first_name: str
    last_name: str
    dni: str
    email: str | None
    phone: str | None
    birth_date: date | None
    medical_history_summary: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
