"""Production analytics dashboard route (Slice 7) — admin-only, read-only."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_analytics_service
from app.core.auth import get_current_admin
from app.schemas.analytics import AnalyticsSummaryResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


@router.get("", response_model=AnalyticsSummaryResponse)
async def get_analytics(
    _: dict = Depends(get_current_admin),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummaryResponse:
    return await service.get_summary()
