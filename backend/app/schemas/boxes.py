"""Pydantic contracts for ``/api/v1/boxes``.

The payload has no ``clinic_id``: the tenant always comes from the verified
session (spec "Agenda clinic scope is server-derived").
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.box import BOX_STATUSES


def _validate_status(value: str) -> str:
    if value not in BOX_STATUSES:
        raise ValueError(f"status must be one of {sorted(BOX_STATUSES)}")
    return value


class BoxCreateRequest(BaseModel):
    """Box creation; the clinic is never sent by the client."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name must not be blank")
        return name


class BoxResponse(BaseModel):
    """Box view returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
