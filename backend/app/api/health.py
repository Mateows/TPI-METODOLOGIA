"""Liveness + database reachability probe (unauthenticated bootstrap proof).

Never logs request bodies or patient data (Ley 25.326 logging prohibition).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """200 + healthy flags when the DB answers; 503 + unhealthy otherwise."""
    from fastapi.responses import JSONResponse

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "app": "healthy", "database": "unhealthy"},
        )
    return {"status": "healthy", "app": "healthy", "database": "healthy"}
