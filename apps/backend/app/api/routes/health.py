"""Health endpoint for the walking skeleton."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.channel import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().service_name)
