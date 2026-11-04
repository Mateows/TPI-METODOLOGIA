"""Task 8.1 — layering guard (design D13, AGENTS.md rule 4).

Every SQLAlchemy query or write lives in ``app/repositories/``. Services and the
bootstrap CLI only orchestrate business rules, so they must never build a
``select(...)``/``func.*`` expression nor call ``execute``/``scalar``/``get``/
``add`` on a database session. The check is AST-based so that unrelated calls
such as ``dict.get`` or ``SecretStr.get_secret_value`` are not false positives:
only calls whose receiver is a session (``db``, ``session``, ``self.db``…) count.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
GUARDED_PACKAGES = ("services", "cli")

# Names a database session is bound to across the codebase.
SESSION_NAMES = frozenset({"db", "session", "test_session"})
FORBIDDEN_SESSION_METHODS = frozenset(
    {"execute", "scalar", "scalars", "get", "add", "add_all", "delete", "begin_nested"}
)
FORBIDDEN_SQLALCHEMY_IMPORTS = frozenset({"select", "func", "update", "delete", "insert"})
FORBIDDEN_BARE_CALLS = frozenset({"select"})


def _guarded_modules() -> list[Path]:
    return sorted(
        path
        for package in GUARDED_PACKAGES
        for path in (APP_DIR / package).glob("*.py")
        if path.name != "__init__.py"
    )


def _is_session(node: ast.expr) -> bool:
    """``db`` / ``session`` or an attribute ending in one (``self.db``)."""
    if isinstance(node, ast.Name):
        return node.id in SESSION_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr in SESSION_NAMES
    return False


def persistence_violations(source: str) -> list[str]:
    """Return a human description of each persistence leak found in ``source``."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module == "sqlalchemy":
            for alias in node.names:
                if alias.name in FORBIDDEN_SQLALCHEMY_IMPORTS:
                    found.append(f"line {node.lineno}: imports sqlalchemy.{alias.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_BARE_CALLS:
                found.append(f"line {node.lineno}: builds {func.id}(...)")
            elif isinstance(func, ast.Attribute):
                if (
                    func.attr in FORBIDDEN_SESSION_METHODS
                    and _is_session(func.value)
                ):
                    found.append(f"line {node.lineno}: calls session.{func.attr}()")
                elif isinstance(func.value, ast.Name) and func.value.id == "func":
                    found.append(f"line {node.lineno}: builds func.{func.attr}(...)")
    return found


def test_guard_detects_queries_and_ignores_unrelated_get_calls():
    """The detector itself: real leaks are flagged, ``dict.get`` is not."""
    leaky = (
        "from sqlalchemy import func, select\n"
        "async def f(db, self):\n"
        "    await db.execute(select(User))\n"
        "    await db.scalar(func.count())\n"
        "    await self.db.get(User, 1)\n"
        "    db.add(x)\n"
    )
    clean = (
        "async def f(db, claims, secret):\n"
        "    claims.get('sub')\n"
        "    secret.get_secret_value()\n"
        "    await db.commit()\n"
        "    await db.flush()\n"
    )

    assert len(persistence_violations(leaky)) == 8
    assert persistence_violations(clean) == []


def test_guarded_packages_are_not_empty():
    names = {path.name for path in _guarded_modules()}
    assert {"auth.py", "users.py", "principal.py", "bootstrap_clinic.py"} <= names


@pytest.mark.parametrize(
    "module", _guarded_modules(), ids=lambda path: f"{path.parent.name}/{path.name}"
)
def test_services_and_cli_delegate_persistence_to_repositories(module: Path):
    violations = persistence_violations(module.read_text(encoding="utf-8"))
    assert violations == [], (
        f"{module.relative_to(APP_DIR.parent)} must use app.repositories (D13): "
        + "; ".join(violations)
    )
