"""Admin notification management routes for Slice 13."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_notification_delivery_service
from app.core.auth import get_current_admin
from app.services.notification_delivery_service import NotificationDeliveryService

router = APIRouter(prefix="/api/admin/notifications", tags=["admin-notifications"])


@router.post("/digest", response_model=dict)
async def trigger_weekly_digest(
    _: dict = Depends(get_current_admin),
    delivery_svc: NotificationDeliveryService = Depends(get_notification_delivery_service),
) -> dict:
    """Trigger digest emails for all follows with notify_digest=True.

    Called by an external cron job (e.g. Render Cron or GitHub Actions scheduled
    workflow) once per week. See HANDOFF.md for setup instructions.
    """
    return await delivery_svc.send_weekly_digest()
