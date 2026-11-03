"""FastAPI entrypoint: app factory + layered router include point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.core.database import get_db
from app.core.errors import register_exception_handlers

__all__ = ["app", "create_app", "get_db"]


def create_app() -> FastAPI:
    """Application factory (C-02+ registers domain routers here)."""
    application = FastAPI(title="TPI Metodologia API")
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    return application


app = create_app()
