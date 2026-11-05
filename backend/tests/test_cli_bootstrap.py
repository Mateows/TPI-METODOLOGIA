"""Tasks 6.1–6.2 — operator-only clinic bootstrap (design D8/D10).

Two properties are proven:
* running the command twice leaves exactly one clinic and one admin user;
* the password never travels through argv, stdout or the returned summary, and
  the API exposes no public route that creates clinics.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import verify_password
from app.models.clinic import Clinic
from app.models.user import User
from app.cli import bootstrap_clinic as cli

BASE_ARGV = [
    "--name",
    "Clínica Ejemplo Sur",
    "--tax-id",
    "30-71234567-8",
    "--email",
    "admin@sur-ejemplo.com",
    "--full-name",
    "Ada Administradora",
]


async def _count_clinics(db, tax_id: str) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Clinic).where(Clinic.tax_id == tax_id)
        )
    ).scalar_one()


async def _single_user(db, email: str) -> User:
    return (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one()


async def test_two_runs_create_exactly_one_clinic_and_one_admin(
    test_session, capsys, monkeypatch
):
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )

    first = await cli.run(BASE_ARGV, db=test_session)
    second = await cli.run(BASE_ARGV, db=test_session)

    assert first == 0
    assert second == 0
    assert await _count_clinics(test_session, "30-71234567-8") == 1

    clinic = (
        await test_session.execute(
            select(Clinic).where(Clinic.tax_id == "30-71234567-8")
        )
    ).scalar_one()
    users = (
        await test_session.execute(
            select(User).where(User.clinic_id == clinic.id)
        )
    ).scalars().all()
    assert len(users) == 1

    admin = users[0]
    assert admin.email == "admin@sur-ejemplo.com"
    assert admin.role == "admin"
    assert admin.is_active is True
    assert admin.full_name == "Ada Administradora"
    assert verify_password("Bootstrap-123", admin.password_hash)

    output = capsys.readouterr().out
    assert "Bootstrap-123" not in output
    assert admin.password_hash not in output


async def test_second_run_reports_the_existing_state(test_session, capsys, monkeypatch):
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )
    await cli.run(BASE_ARGV, db=test_session)
    capsys.readouterr()

    await cli.run(BASE_ARGV, db=test_session)

    output = capsys.readouterr().out.lower()
    assert "already exists" in output or "existe" in output


async def test_password_comes_from_the_hidden_prompt_when_env_is_absent(
    test_session, monkeypatch
):
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", None)
    asked: list[int] = []

    def _prompt() -> str:
        asked.append(1)
        return "Prompt-Secreta-123"

    code = await cli.run(BASE_ARGV, db=test_session, password_provider=_prompt)

    assert code == 0
    assert asked == [1]
    admin = await _single_user(test_session, "admin@sur-ejemplo.com")
    assert verify_password("Prompt-Secreta-123", admin.password_hash)


async def test_password_is_never_accepted_as_a_command_line_argument(
    test_session, monkeypatch
):
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )

    with pytest.raises(SystemExit) as excinfo:
        await cli.run(
            [*BASE_ARGV, "--password", "Filtrada-123"], db=test_session
        )

    assert excinfo.value.code == 2
    assert await _count_clinics(test_session, "30-71234567-8") == 0


async def test_bootstrap_is_idempotent_by_tax_id_and_email_independently(
    test_session, monkeypatch
):
    """Same clinic + new admin -> new user in the same clinic; no second clinic."""
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )
    await cli.run(BASE_ARGV, db=test_session)

    second_admin = [
        *BASE_ARGV[:5],
        "segundo@sur-ejemplo.com",
        "--full-name",
        "Segunda Administradora",
    ]
    code = await cli.run(second_admin, db=test_session)

    assert code == 0
    assert await _count_clinics(test_session, "30-71234567-8") == 1
    clinic = (
        await test_session.execute(
            select(Clinic).where(Clinic.tax_id == "30-71234567-8")
        )
    ).scalar_one()
    emails = (
        await test_session.execute(
            select(User.email).where(User.clinic_id == clinic.id)
        )
    ).scalars().all()
    assert set(emails) == {"admin@sur-ejemplo.com", "segundo@sur-ejemplo.com"}


async def test_slug_is_derived_from_the_name_when_not_provided(
    test_session, monkeypatch
):
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )

    await cli.run(BASE_ARGV, db=test_session)

    clinic = (
        await test_session.execute(
            select(Clinic).where(Clinic.tax_id == "30-71234567-8")
        )
    ).scalar_one()
    assert clinic.slug == "clinica-ejemplo-sur"


async def test_short_bootstrap_password_is_refused(test_session, monkeypatch):
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("corta"))

    code = await cli.run(BASE_ARGV, db=test_session)

    assert code != 0
    assert await _count_clinics(test_session, "30-71234567-8") == 0


async def test_no_public_route_creates_clinics(client, test_session):
    """Spec scenario: an unauthenticated caller finds no clinic-creation route."""
    from app.main import app

    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and "clinic" in path.lower():
            raise AssertionError(f"public clinic creation route exposed: {path}")

    response = await client.post(
        "/api/v1/clinics",
        json={"name": "Intrusa", "tax_id": "30-00000000-0", "slug": "intrusa"},
    )

    assert response.status_code == 404
    assert (
        await test_session.execute(
            select(func.count()).select_from(Clinic).where(Clinic.tax_id == "30-00000000-0")
        )
    ).scalar_one() == 0


async def test_cli_output_never_contains_the_stored_hash(
    test_session, capsys, monkeypatch
):
    """6.2: the operational output never leaks credential material."""
    monkeypatch.setattr(
        settings, "BOOTSTRAP_ADMIN_PASSWORD", SecretStr("Bootstrap-123")
    )

    await cli.run(BASE_ARGV, db=test_session)

    admin = await _single_user(test_session, "admin@sur-ejemplo.com")
    output = capsys.readouterr().out
    assert admin.password_hash not in output
    assert "Bootstrap-123" not in output
