"""Pydantic contracts for ``/api/v1/users`` (admin-only, intra-clinic, D5/D6).

Roles are validated against ``USER_ROLES`` (the single source of truth) instead
of duplicating a ``Literal``; an unknown role answers 422 like any other invalid
payload. ``extra="forbid"`` rejects a client-supplied ``clinic_id``: the tenant
always comes from the verified session.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import USER_ROLES


def _validate_role(value: str) -> str:
    if value not in USER_ROLES:
        raise ValueError(f"role must be one of {sorted(USER_ROLES)}")
    return value


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    local, _, domain = email.partition("@")
    if not local or not domain or "@" in domain or any(c.isspace() for c in email):
        raise ValueError("invalid email address")
    return email


class UserCreateRequest(BaseModel):
    """Initial account for a teammate; the clinic is never sent by the client."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="dentist")
    # bcrypt accepts at most 72 bytes (same rule as the password change form).
    password: str = Field(min_length=8, max_length=72)

    @field_validator("role")
    @classmethod
    def _role(cls, value: str) -> str:
        return _validate_role(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class UserUpdateRequest(BaseModel):
    """Partial update: any subset of name, role and state (task 5.2)."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def _role(cls, value: str | None) -> str | None:
        return None if value is None else _validate_role(value)


class UserResponse(BaseModel):
    """Administration view: identity and role, never credential material."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
