"""Intra-clinic user administration (design D5/D6/D10).

Every query is scoped by ``principal.clinic_id``; a foreign id answers exactly
like an absent one. The service only flushes: the router owns the commit, as in
``app.services.auth``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DuplicateEmail, LastAdminError, TenantViolation
from app.core.security import hash_password
from app.models.user import User
from app.schemas.users import UserCreateRequest, UserUpdateRequest
from app.services.principal import Principal
from app.services.tenant import TenantScopedRepository


async def create_user(
    db: AsyncSession, principal: Principal, payload: UserCreateRequest
) -> User:
    """Create a user inside the caller's clinic (never a client-supplied one)."""
    email = payload.email  # already normalized by the schema
    existing = await db.execute(select(User.id).where(User.email == email))
    if existing.first() is not None:
        # Design D6: the conflict must not reveal which clinic owns the email.
        raise DuplicateEmail()

    user = User(
        clinic_id=principal.clinic_id,
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_active=True,
    )
    try:
        # Savepoint: a raced duplicate must not poison the request transaction.
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError as exc:
        raise DuplicateEmail() from exc
    return user


async def list_users(db: AsyncSession, principal: Principal) -> list[User]:
    """List only users of the principal's clinic, in a stable order."""
    repo = TenantScopedRepository(User, db, principal)
    result = await db.execute(repo.scoped().order_by(User.email))
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession,
    principal: Principal,
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
) -> User:
    """Update name, role and/or state of a user of the caller's clinic.

    A foreign id is a ``TenantViolation`` (404, identical to an absent one). The
    clinic must always keep at least one active ``admin``, so the last one can
    neither be demoted nor deactivated (task 5.2).
    """
    repo = TenantScopedRepository(User, db, principal)
    user = await repo.get(user_id)
    if user is None:
        raise TenantViolation("resource not found")

    new_role = payload.role if payload.role is not None else user.role
    new_active = payload.is_active if payload.is_active is not None else user.is_active
    loses_admin = user.role == "admin" and (new_role != "admin" or not new_active)
    if loses_admin:
        remaining = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.clinic_id == principal.clinic_id,
                User.role == "admin",
                User.is_active.is_(True),
                User.id != user.id,
            )
        )
        if not remaining:
            raise LastAdminError()

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    user.role = new_role
    user.is_active = new_active
    await db.flush()
    return user
