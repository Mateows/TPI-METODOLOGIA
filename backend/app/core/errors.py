"""Semantic domain errors with a stable ``code`` (design D10).

Every failure that crosses the API boundary is expressed as ``{detail, code}``.
``code`` is the machine-readable contract; ``detail`` is human text that never
contains SQL, driver output, credentials or patient data (Ley 25.326).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class DomainError(Exception):
    """Base class for expected business failures (never a programming error)."""

    status_code: int = 500
    code: str = "internal_error"
    default_detail: str = "unexpected error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class AuthenticationError(DomainError):
    """The caller is not (or no longer) an authenticated identity."""

    status_code = 401
    code = "authentication_failed"
    default_detail = "authentication required"


class InvalidCredentials(AuthenticationError):
    """Unknown email or wrong password — deliberately indistinguishable."""

    code = "invalid_credentials"
    default_detail = "invalid credentials"


class SessionRevoked(AuthenticationError):
    """Refresh session unknown, expired, rotated or revoked."""

    code = "session_revoked"
    default_detail = "session is no longer valid"


class AuthorizationError(DomainError):
    """Authenticated but not allowed (role, inactive clinic)."""

    status_code = 403
    code = "forbidden"
    default_detail = "operation not permitted"


class TenantViolation(DomainError):
    """Record of another clinic — answered exactly like a missing record."""

    status_code = 404
    code = "not_found"
    default_detail = "resource not found"


class PatientNotFound(DomainError):
    """Patient does not exist in the active clinic (indistinguishable from TenantViolation, D6)."""

    status_code = 404
    code = "not_found"
    default_detail = "resource not found"


class DuplicateEmail(DomainError):
    """Email already belongs to a user (D6); the owning clinic is not revealed."""

    status_code = 409
    code = "duplicate_email"
    default_detail = "email already registered"


class DuplicateDni(DomainError):
    """A patient with the same DNI already exists in the active clinic (D6)."""

    status_code = 409
    code = "duplicate_dni"
    default_detail = "a patient with that DNI already exists in this clinic"


class LastAdminError(DomainError):
    """The change would leave a clinic without an active administrator.

    Conflict, not validation: the payload is well formed but it breaks the
    clinic's authorization invariant (spec: only an ``admin`` manages users).
    """

    status_code = 409
    code = "last_admin"
    default_detail = "clinic must keep at least one active administrator"


class AppointmentNotFound(DomainError):
    """Appointment does not exist in the active clinic (indistinguishable from TenantViolation)."""

    status_code = 404
    code = "not_found"
    default_detail = "resource not found"


class DentistNotFound(DomainError):
    """Dentist does not exist in the active clinic (indistinguishable from TenantViolation)."""

    status_code = 404
    code = "not_found"
    default_detail = "resource not found"


class BoxNotFound(DomainError):
    """Box does not exist in the active clinic (indistinguishable from TenantViolation)."""

    status_code = 404
    code = "not_found"
    default_detail = "resource not found"


class AppointmentOverlap(DomainError):
    """Appointment interval overlaps an existing appointment for the dentist or box (RN-01)."""

    status_code = 409
    code = "appointment_overlap"
    default_detail = "appointment overlaps with an existing appointment for this dentist or box"


class InvalidTimeRange(DomainError):
    """Appointment start_time must be before end_time (RN-07)."""

    status_code = 422
    code = "invalid_time_range"
    default_detail = "end_time must be after start_time"


class InvalidAppointmentTransition(DomainError):
    """Appointment state transition is not allowed by the transition matrix."""

    status_code = 409
    code = "invalid_appointment_transition"
    default_detail = "invalid appointment transition"


def _error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"detail": detail, "code": code}
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Attach the D10 contract handlers to an application instance."""

    @application.exception_handler(DomainError)
    async def _domain_error_handler(
        _request: Request, exc: DomainError
    ) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.detail)

    @application.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        # Field locations are safe, but the message is kept stable and generic so
        # no internal type/validator text leaks into the contract.
        return _error_response(422, "validation_error", "invalid request payload")

    @application.exception_handler(SQLAlchemyError)
    async def _persistence_error_handler(
        _request: Request, _exc: SQLAlchemyError
    ) -> JSONResponse:
        # Never propagate SQL statements, table/column names or driver messages.
        return _error_response(500, "internal_error", "internal server error")
