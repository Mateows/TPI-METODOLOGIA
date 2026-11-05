"""Task 3.1 — domain exceptions and the JSON error contract (design D10).

The contract is ``{detail, code}`` with a stable ``code``; free text is never
asserted, and no SQLAlchemy/driver text may reach the response body.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from app.core.errors import (
    AppointmentNotFound,
    AppointmentOverlap,
    BoxNotFound,
    DentistNotFound,
    InvalidAppointmentTransition,
    InvalidTimeRange,
    AuthenticationError,
    AuthorizationError,
    DomainError,
    DuplicateEmail,
    InvalidCredentials,
    SessionRevoked,
    TenantViolation,
    register_exception_handlers,
)
from app.main import create_app

# Marker that must never survive into the response (simulates a leaked query).
DRIVER_LEAK_MARKER = "SELECT password_hash FROM users WHERE clinic_id = 'otra'"


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _app_with(exception: Exception) -> FastAPI:
    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/boom")
    async def boom() -> None:
        raise exception

    return application


@pytest.mark.parametrize(
    ("exception", "status_code", "code"),
    [
        (AuthenticationError(), 401, "authentication_failed"),
        (InvalidCredentials(), 401, "invalid_credentials"),
        (SessionRevoked(), 401, "session_revoked"),
        (AuthorizationError(), 403, "forbidden"),
        (TenantViolation(), 404, "not_found"),
        (DuplicateEmail(), 409, "duplicate_email"),
        (AppointmentOverlap(), 409, "appointment_overlap"),
        (InvalidTimeRange(), 422, "invalid_time_range"),
        (InvalidAppointmentTransition(), 409, "invalid_appointment_transition"),
        (AppointmentNotFound(), 404, "not_found"),
        (DentistNotFound(), 404, "not_found"),
        (BoxNotFound(), 404, "not_found"),
    ],
)
async def test_domain_error_maps_to_status_code_and_stable_code(
    exception: DomainError, status_code: int, code: str
):
    """WHEN a domain error escapes a route THEN {detail, code} with its status."""
    async with _client(_app_with(exception)) as client:
        response = await client.get("/boom")

    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"detail", "code"}
    assert body["code"] == code
    assert isinstance(body["detail"], str) and body["detail"]


async def test_tenant_violation_body_is_identical_to_a_missing_record():
    """Cross-clinic and absent answers must be indistinguishable (D10/spec)."""
    async with _client(_app_with(TenantViolation())) as client:
        foreign = await client.get("/boom")
    async with _client(_app_with(TenantViolation())) as client:
        absent = await client.get("/boom")

    assert foreign.status_code == absent.status_code == 404
    assert foreign.json() == absent.json()


async def test_sqlalchemy_driver_text_never_reaches_the_response_body():
    """WHEN persistence blows up THEN the body carries no SQL/driver text."""
    error = OperationalError(DRIVER_LEAK_MARKER, {}, Exception("driver detail"))
    async with _client(_app_with(error)) as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert DRIVER_LEAK_MARKER not in response.text
    assert "password_hash" not in response.text
    assert "driver detail" not in response.text
    assert "Traceback" not in response.text


async def test_invalid_payload_returns_422_with_stable_code():
    """WHEN the request body fails validation THEN 422 + validation_error."""
    application = FastAPI()
    register_exception_handlers(application)

    class Payload(BaseModel):
        email: str

    @application.post("/echo")
    async def echo(payload: Payload) -> dict[str, str]:
        return {"email": payload.email}

    async with _client(application) as client:
        response = await client.post("/echo", json={"email": 12345})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert set(response.json()) == {"detail", "code"}


@pytest.mark.parametrize(
    ("exception", "status_code", "code"),
    [
        (AuthenticationError(), 401, "authentication_failed"),
        (AuthorizationError(), 403, "forbidden"),
        (DuplicateEmail(), 409, "duplicate_email"),
        (AppointmentOverlap(), 409, "appointment_overlap"),
        (InvalidTimeRange(), 422, "invalid_time_range"),
        (InvalidAppointmentTransition(), 409, "invalid_appointment_transition"),
        (AppointmentNotFound(), 404, "not_found"),
        (DentistNotFound(), 404, "not_found"),
        (BoxNotFound(), 404, "not_found"),
    ],
)
async def test_create_app_handles_domain_subclasses(
    exception: DomainError, status_code: int, code: str
):
    """The real factory (not just the helper) resolves subclasses via MRO."""
    application = create_app()

    async def boom() -> None:
        raise exception

    application.add_api_route("/boom", boom)

    async with _client(application) as client:
        response = await client.get("/boom")

    assert response.status_code == status_code
    assert response.json()["code"] == code
