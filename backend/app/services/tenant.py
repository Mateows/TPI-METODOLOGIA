"""Explicit tenant scoping for reads and writes (design D5).

No implicit ORM magic: every query states ``clinic_id == principal.clinic_id``
so the isolation rule is auditable in one place and testable in isolation.

``TenantScopedRepository`` lives in ``app.repositories.base`` (design D13) and
is re-exported here for compatibility; ``resolve_clinic_id`` is a business rule
and stays in the services layer.
"""

from __future__ import annotations

import uuid

from app.core.errors import TenantViolation
from app.repositories.base import TenantScopedRepository
from app.services.principal import Principal

__all__ = ["TenantScopedRepository", "resolve_clinic_id"]


def resolve_clinic_id(
    principal: Principal, requested: uuid.UUID | None
) -> uuid.UUID:
    """Return the server-side clinic, refusing a conflicting client value.

    ``None`` means "the caller did not send one" and is fine; a different value
    is never trusted, so the request fails closed instead of being retargeted
    (spec: conflicting client clinic is rejected without any change).
    """
    if requested is not None and requested != principal.clinic_id:
        raise TenantViolation("resource not found")
    return principal.clinic_id
