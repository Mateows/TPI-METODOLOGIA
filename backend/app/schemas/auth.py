"""Pydantic contracts for the auth endpoints (strict, no ``extra`` fields).

Response models never include password material or refresh hashes.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Email is globally unique, so no clinic selector is needed (D6)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Session issued to the client; the refresh value is shown only once (D3)."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    role: str


class RefreshRequest(BaseModel):
    """The opaque refresh value; unknown/rotated values answer 401 (D3)."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=512)


class ClinicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class MeResponse(BaseModel):
    """Self-profile: only the caller's identity, clinic and role (spec)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    clinic: ClinicSummary


class PasswordChangeRequest(BaseModel):
    """Self-service password change; bcrypt accepts at most 72 bytes."""

    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)
