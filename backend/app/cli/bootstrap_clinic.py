"""``python -m app.cli.bootstrap_clinic`` — operator-only clinic provisioning.

Design D8:
* idempotent by ``clinic.tax_id`` and ``user.email``: running it twice leaves
  exactly one clinic and one admin account;
* the initial password comes from ``BOOTSTRAP_ADMIN_PASSWORD`` or from a hidden
  prompt, **never** from an argument — argv is visible in the shell history and
  in the process table;
* the command only prints identifiers and state, never the password or its hash;
* there is no HTTP route that creates clinics.

It is the only supported way to create the first tenant of an installation.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import re
import sys
import unicodedata
from collections.abc import Callable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.clinics import ClinicRepository
from app.repositories.users import UserRepository

# Same bounds as the API contract (app/schemas/users.py): a weak or oversized
# bootstrap password must be refused before anything is persisted.
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72
MAX_SLUG_LENGTH = 100
SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.bootstrap_clinic",
        description=(
            "Create (or reuse) a clinic and its first admin account. "
            "The password is read from BOOTSTRAP_ADMIN_PASSWORD or prompted; "
            "it is never accepted as an argument."
        ),
    )
    parser.add_argument("--name", required=True, help="clinic display name")
    parser.add_argument(
        "--tax-id", required=True, help="clinic tax id (CUIT); idempotency key"
    )
    parser.add_argument(
        "--email", required=True, help="admin email; idempotency key"
    )
    parser.add_argument(
        "--full-name", required=True, dest="full_name", help="admin full name"
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="public portal slug (derived from --name when omitted, D7)",
    )
    return parser


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse argv. An unknown option (e.g. ``--password``) exits with code 2."""
    return _build_parser().parse_args(argv)


def _slugify(value: str) -> str:
    """ASCII, lowercase, hyphen-separated slug derived from the clinic name."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug or "clinica"


def _slug_problem(slug: str) -> str | None:
    """Return a human reason when a custom clinic slug is unacceptable, else ``None``.

    Application-level validation: slugs are reserved for the public booking portal
    (C-09 / D7). They must be lowercase ASCII alphanumeric with hyphens, 1 to 100
    chars, and without consecutive or leading/trailing hyphens. Keeping this
    restriction in the application layer avoids unnecessary database schema migrations.
    """
    if not slug:
        return "slug cannot be empty"
    if len(slug) > MAX_SLUG_LENGTH:
        return f"slug must be at most {MAX_SLUG_LENGTH} characters"
    if not SLUG_REGEX.fullmatch(slug):
        return "slug must contain only lowercase letters, digits, and single hyphens between words"
    return None


async def _unique_slug(db: AsyncSession, base: str) -> str:
    """Return ``base`` or ``base-2``, ``base-3``… so the unique slug holds."""
    candidate = base
    suffix = 2
    clinics = ClinicRepository(db)
    while await clinics.slug_exists(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _resolve_password(
    password_provider: Callable[[], str] | None,
) -> str:
    """Env var first, then the injected provider (tests), then a hidden prompt."""
    configured = settings.BOOTSTRAP_ADMIN_PASSWORD
    if configured is not None and configured.get_secret_value():
        return configured.get_secret_value()
    if password_provider is not None:
        return password_provider()
    # getpass never echoes the value and keeps it out of argv/ps.
    return getpass.getpass("Initial admin password: ")


def _password_problem(password: str) -> str | None:
    """Return a human reason when the password is unacceptable, else ``None``."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"password must be at most {MAX_PASSWORD_BYTES} bytes"
    return None


async def _bootstrap(
    db: AsyncSession,
    args: argparse.Namespace,
    password_provider: Callable[[], str] | None,
) -> int:
    """Apply the idempotent provisioning and return a process exit code."""
    tax_id = args.tax_id.strip()
    email = args.email.strip().lower()
    name = args.name.strip()
    full_name = args.full_name.strip()

    if args.slug:
        slug_problem = _slug_problem(args.slug.strip())
        if slug_problem is not None:
            print(f"error: {slug_problem}", file=sys.stderr)
            return 2

    clinics = ClinicRepository(db)
    users = UserRepository(db)
    clinic = await clinics.get_by_tax_id(tax_id)
    account = await users.get_with_clinic_by_email(email)
    existing_user = None if account is None else account[0]

    # The email is globally unique (D6): reusing it in another tenant would
    # hijack an identity, so it is refused instead of silently re-scoped.
    if existing_user is not None and (
        clinic is None or existing_user.clinic_id != clinic.id
    ):
        print(
            f"error: email {email} is already registered for another clinic",
            file=sys.stderr,
        )
        return 1

    if clinic is not None and existing_user is not None:
        # Nothing to do: report the existing state without any secret.
        print(
            f"clinic already exists: {name!r} "
            f"(tax_id={tax_id}, id={clinic.id})"
        )
        print(
            f"admin user already exists: {email} "
            f"(id={existing_user.id}, role={existing_user.role})"
        )
        return 0

    password = _resolve_password(password_provider)
    problem = _password_problem(password)
    if problem is not None:
        # Never echo the value, only the rule it violates.
        print(f"error: {problem}", file=sys.stderr)
        return 2

    if clinic is None:
        raw_slug = args.slug.strip() if args.slug else _slugify(name)
        slug = await _unique_slug(db, raw_slug)
        clinic = Clinic(name=name, slug=slug, tax_id=tax_id, is_active=True)
        await clinics.add(clinic)
        print(f"clinic created: {name!r} (tax_id={tax_id}, slug={slug}, id={clinic.id})")
    else:
        print(
            f"clinic already exists: {clinic.name!r} "
            f"(tax_id={tax_id}, id={clinic.id})"
        )

    admin = User(
        clinic_id=clinic.id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="admin",
        is_active=True,
    )
    await users.add(admin)
    print(f"admin user created: {email} (id={admin.id}, role=admin)")
    return 0


async def run(
    argv: Sequence[str] | None = None,
    *,
    db: AsyncSession | None = None,
    password_provider: Callable[[], str] | None = None,
) -> int:
    """Provision the clinic and its first admin; return a process exit code.

    ``db`` is injected by the integration tests; the real command opens its own
    session from ``SessionLocal`` (the operator database).
    """
    args = _parse_args(argv)

    if db is not None:
        code = await _bootstrap(db, args, password_provider)
        if code == 0:
            await db.commit()
        return code

    from app.core.database import SessionLocal

    async with SessionLocal() as session:
        code = await _bootstrap(session, args, password_provider)
        if code == 0:
            await session.commit()
        else:
            await session.rollback()
    return code


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous entrypoint used by ``python -m app.cli.bootstrap_clinic``."""
    return asyncio.run(run(argv))


if __name__ == "__main__":  # pragma: no cover - exercised as a process
    sys.exit(main())
