"""FastAPI entrypoint: app factory + layered router include point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.database import get_db

__all__ = ["app", "create_app", "get_db"]


def create_app() -> FastAPI:
    """Application factory (C-02+ registers domain routers here)."""
    application = FastAPI(title="TPI Metodologia API")
    application.include_router(health_router)
    return application


app = create_app()
