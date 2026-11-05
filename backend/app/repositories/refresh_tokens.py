"""``RefreshToken`` persistence (design D3/D13).

Only hashes are stored or queried; raw refresh values never reach this layer.
``get_with_account_by_hash`` is global by design: it runs before a ``Principal``
exists, and the service re-checks that the row's clinic matches its user's.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.refresh_token import RefreshToken
from app.models.user import User


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_with_account_by_hash(
        self, token_hash: str
    ) -> tuple[RefreshToken, User, Clinic] | None:
        """Load the refresh row with its user and clinic (global, by hash)."""
        row = (
            await self.db.execute(
                select(RefreshToken, User, Clinic)
                .join(User, RefreshToken.user_id == User.id)
                .join(Clinic, User.clinic_id == Clinic.id)
                .where(RefreshToken.token_hash == token_hash)
            )
        ).first()
        return None if row is None else (row[0], row[1], row[2])

    async def revoke_family(self, family_id: uuid.UUID, revoked_at: datetime) -> int:
        """Revoke every still-live row of ``family_id``; return how many."""
        rows = (
            await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.family_id == family_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalars().all()
        for row in rows:
            row.revoked_at = revoked_at
        await self.db.flush()
        return len(rows)

    async def revoke_all_for_user(self, user_id: uuid.UUID, revoked_at: datetime) -> int:
        """Revoke every still-live row of ``user_id``; return how many."""
        rows = (
            await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalars().all()
        for row in rows:
            row.revoked_at = revoked_at
        await self.db.flush()
        return len(rows)
