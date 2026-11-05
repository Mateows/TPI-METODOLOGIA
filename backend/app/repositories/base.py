"""Explicit tenant scoping for reads and writes (design D5).

No implicit ORM magic: every query states ``clinic_id == principal.clinic_id``
so the isolation rule is auditable in one place and testable in isolation.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class ClinicScope(Protocol):
    """Anything that carries the server-side tenant (e.g. ``Principal``).

    Declared structurally so the persistence layer does not import the services
    layer (``app.services.principal`` depends on repositories, not vice versa).
    """

    @property
    def clinic_id(self) -> uuid.UUID: ...


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
        principal: ClinicScope,
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
