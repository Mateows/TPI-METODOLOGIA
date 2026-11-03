"""Explicit tenant scoping for reads and writes (design D5).

No implicit ORM magic: every query states ``clinic_id == principal.clinic_id``
so the isolation rule is auditable in one place and testable in isolation.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import TenantViolation
from app.services.principal import Principal

ModelT = TypeVar("ModelT")


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


class TenantScopedRepository(Generic[ModelT]):
    """Minimal read base for clinic-owned models.

    ``get`` answers ``None`` for a record of another clinic, exactly like an
    absent id, so cross-clinic disclosure is impossible (spec scenario
    "Foreign identifier is indistinguishable from absent").
    """

    def __init__(
        self,
        model: type[ModelT],
        db: AsyncSession,
        principal: Principal,
    ) -> None:
        if not hasattr(model, "clinic_id"):
            raise TypeError(
                f"{model.__name__} has no clinic_id; it cannot be tenant-scoped"
            )
        self.model = model
        self.db = db
        self.principal = principal

    def scoped(self, *criteria: Any) -> Select[tuple[ModelT]]:
        """Build a SELECT already filtered by the principal's clinic."""
        clinic_column = self.model.clinic_id  # type: ignore[attr-defined]
        return select(self.model).where(
            clinic_column == self.principal.clinic_id, *criteria
        )

    async def get(self, record_id: uuid.UUID) -> ModelT | None:
        identifier = self.model.id  # type: ignore[attr-defined]
        result = await self.db.execute(self.scoped(identifier == record_id))
        return result.scalar_one_or_none()

    async def list(self, *criteria: Any) -> Sequence[ModelT]:
        result = await self.db.execute(self.scoped(*criteria))
        return result.scalars().all()
