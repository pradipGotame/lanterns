"""
routers/health.py
=================
GET /health — simple liveness check.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from config import UPLOAD_ROOT
from models import HealthResponse

router = APIRouter(tags=["System"])


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check if the API is running."""
    return HealthResponse(
        status="ok",
        message="Project Manager API is running",
        upload_dir=str(UPLOAD_ROOT),
        timestamp=_utc_iso(),
    )
