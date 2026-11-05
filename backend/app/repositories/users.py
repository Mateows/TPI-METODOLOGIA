"""``User`` persistence (design D4/D5/D6/D13).

Global lookups (``get_with_clinic_by_email``, ``get_with_clinic_by_id``,
``email_exists``) exist only for the moments before a ``Principal`` is known —
login, per-request principal resolution and the global email uniqueness of D6.
Every other read takes ``clinic_id`` explicitly.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_with_clinic_by_email(self, email: str) -> tuple[User, Clinic] | None:
        """Global lookup by (already normalized) email, for login only."""
        row = (
            await self.db.execute(
                select(User, Clinic)
                .join(Clinic, User.clinic_id == Clinic.id)
                .where(User.email == email)
            )
        ).first()
        return None if row is None else (row[0], row[1])

    async def get_with_clinic_by_id(self, user_id: uuid.UUID) -> tuple[User, Clinic] | None:
        """Global lookup by id, used to resolve the principal of a request (D4)."""
        row = (
            await self.db.execute(
                select(User, Clinic)
                .join(Clinic, User.clinic_id == Clinic.id)
                .where(User.id == user_id)
            )
        ).first()
        return None if row is None else (row[0], row[1])

    async def email_exists(self, email: str) -> bool:
        """Global uniqueness check (D6): the email may belong to any clinic."""
        existing = await self.db.execute(select(User.id).where(User.email == email))
        return existing.first() is not None

    async def add(self, user: User) -> User:
        """Insert ``user`` inside a savepoint and flush.

        Savepoint: a raced duplicate must not poison the request transaction.
        ``IntegrityError`` propagates so the caller maps it to its domain error.
        """
        async with self.db.begin_nested():
            self.db.add(user)
            await self.db.flush()
        return user

    async def list_for_clinic(self, clinic_id: uuid.UUID) -> list[User]:
        """Users of ``clinic_id`` only, in a stable order (by email)."""
        result = await self.db.execute(
            select(User).where(User.clinic_id == clinic_id).order_by(User.email)
        )
        return list(result.scalars().all())

    async def get_in_clinic(self, clinic_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        """A foreign id answers ``None``, exactly like an absent one (D5)."""
        result = await self.db.execute(
            select(User).where(User.clinic_id == clinic_id, User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def count_other_active_admins(
        self, clinic_id: uuid.UUID, excluding_user_id: uuid.UUID
    ) -> int:
        """Active admins of ``clinic_id`` other than ``excluding_user_id``."""
        remaining = await self.db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.clinic_id == clinic_id,
                User.role == "admin",
                User.is_active.is_(True),
                User.id != excluding_user_id,
            )
        )
        return int(remaining or 0)
