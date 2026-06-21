"""Listener follow management routes (Slice 9)."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.api.dependencies import get_follow_service
from app.schemas.follow import FollowPublicView
from app.services.follow_service import FollowService

router = APIRouter(prefix="/api/follows", tags=["follows"])


class UpdateFollowRequest(BaseModel):
    notification_channel: str


def _get_listener_identity(
    wp_listener_discord_id: str | None = Cookie(default=None),
    wp_listener_email: str | None = Cookie(default=None),
) -> dict:
    if not wp_listener_discord_id and not wp_listener_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"discord_user_id": wp_listener_discord_id, "email": wp_listener_email}


# /confirm must be registered before /{follow_id} to avoid slug capture.
@router.post("/confirm", response_model=dict)
async def confirm_email_follow(
    token: str = Query(...),
    service: FollowService = Depends(get_follow_service),
) -> dict:
    follow = await service.confirm_email(token)
    return {"ok": True, "follow_id": follow.id, "channel_slug": follow.channel_slug}


@router.get("", response_model=list[FollowPublicView])
async def list_follows(
    identity: dict = Depends(_get_listener_identity),
    service: FollowService = Depends(get_follow_service),
) -> list[FollowPublicView]:
    return await service.get_listener_follows(
        discord_user_id=identity["discord_user_id"],
        email=identity["email"],
    )


@router.patch("/{follow_id}", response_model=FollowPublicView)
async def update_follow(
    follow_id: str,
    body: UpdateFollowRequest,
    identity: dict = Depends(_get_listener_identity),
    service: FollowService = Depends(get_follow_service),
) -> FollowPublicView:
    return await service.update_follow(
        follow_id=follow_id,
        discord_user_id=identity["discord_user_id"],
        email=identity["email"],
        notification_channel=body.notification_channel,
    )


@router.delete("/{follow_id}")
async def delete_follow(
    follow_id: str,
    identity: dict = Depends(_get_listener_identity),
    service: FollowService = Depends(get_follow_service),
) -> Response:
    await service.delete_follow(
        follow_id=follow_id,
        discord_user_id=identity["discord_user_id"],
        email=identity["email"],
    )
    return Response(status_code=204)
