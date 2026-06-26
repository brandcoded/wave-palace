"""Routes for Slice 12 — Logged-In Dashboard (me/* endpoints)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import (
    get_channel_service,
    get_channel_save_repository,
    get_listen_history_service,
    get_notification_repository,
    get_recommendation_service,
    get_follow_repository,
)
from app.core.auth import get_current_user, get_optional_user
from app.repositories.channel_save_repository import ChannelSaveRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.user import UserDocument
from app.services.channel_service import ChannelService
from app.services.listen_history_service import ListenHistoryService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/me", tags=["me"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RecordPlayBody(BaseModel):
    channel_slug: str
    track_title: Optional[str] = None
    track_artist: Optional[str] = None
    session_key: Optional[str] = None


class MergeHistoryBody(BaseModel):
    session_key: str


class MarkNotifReadBody(BaseModel):
    read: bool = True


# ---------------------------------------------------------------------------
# Listen history
# ---------------------------------------------------------------------------

@router.post("/history", status_code=201)
async def record_history(
    body: RecordPlayBody,
    user: Optional[UserDocument] = Depends(get_optional_user),
    history_svc: ListenHistoryService = Depends(get_listen_history_service),
):
    await history_svc.record_play(
        user_id=user.id if user else None,
        session_key=body.session_key,
        channel_slug=body.channel_slug,
        track_title=body.track_title,
        track_artist=body.track_artist,
    )
    return {"ok": True}


@router.post("/history/merge")
async def merge_history(
    body: MergeHistoryBody,
    user: UserDocument = Depends(get_current_user),
    history_svc: ListenHistoryService = Depends(get_listen_history_service),
):
    merged = await history_svc.merge_anonymous(body.session_key, user.id)
    return {"merged": merged}


@router.get("/history")
async def get_history(
    user: UserDocument = Depends(get_current_user),
    history_svc: ListenHistoryService = Depends(get_listen_history_service),
):
    return await history_svc.get_history(user.id)


# ---------------------------------------------------------------------------
# Saved channels
# ---------------------------------------------------------------------------

@router.post("/saves/{slug}", status_code=204)
async def save_channel(
    slug: str,
    user: UserDocument = Depends(get_current_user),
    save_repo: ChannelSaveRepository = Depends(get_channel_save_repository),
    channel_svc: ChannelService = Depends(get_channel_service),
):
    channel = await channel_svc.get_published_by_slug(slug)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    await save_repo.save(user.id, slug)


@router.delete("/saves/{slug}", status_code=204)
async def unsave_channel(
    slug: str,
    user: UserDocument = Depends(get_current_user),
    save_repo: ChannelSaveRepository = Depends(get_channel_save_repository),
):
    await save_repo.unsave(user.id, slug)


@router.get("/saves")
async def get_saves(
    user: UserDocument = Depends(get_current_user),
    save_repo: ChannelSaveRepository = Depends(get_channel_save_repository),
):
    slugs = await save_repo.get_saved_slugs(user.id)
    return {"slugs": slugs}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications")
async def get_notifications(
    user: UserDocument = Depends(get_current_user),
    notif_repo: NotificationRepository = Depends(get_notification_repository),
):
    notifs = await notif_repo.get_by_user(user.id)
    unread_count = await notif_repo.unread_count(user.id)
    return {
        "notifications": [n.model_dump() for n in notifs],
        "unread_count": unread_count,
    }


@router.patch("/notifications/{notif_id}")
async def mark_notification_read(
    notif_id: str,
    body: MarkNotifReadBody,
    user: UserDocument = Depends(get_current_user),
    notif_repo: NotificationRepository = Depends(get_notification_repository),
):
    found = await notif_repo.mark_read(notif_id, user.id)
    if not found:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


@router.post("/notifications/mark-all-read")
async def mark_all_read(
    user: UserDocument = Depends(get_current_user),
    notif_repo: NotificationRepository = Depends(get_notification_repository),
):
    count = await notif_repo.mark_all_read(user.id)
    return {"marked": count}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.get("/recommendations")
async def get_recommendations(
    user: UserDocument = Depends(get_current_user),
    rec_svc: RecommendationService = Depends(get_recommendation_service),
):
    recs = await rec_svc.get_recommendations(user)
    return {"recommendations": recs}


# ---------------------------------------------------------------------------
# Followed channels (bridges Slice 9 follows → me namespace)
# ---------------------------------------------------------------------------

@router.get("/follows")
async def get_my_follows(
    user: UserDocument = Depends(get_current_user),
    follow_repo=Depends(get_follow_repository),
):
    follows = await follow_repo.get_by_identity(
        discord_user_id=user.discord_user_id,
        email=user.email,
    )
    confirmed = [f for f in follows if f.confirmed]
    return {"slugs": [f.channel_slug for f in confirmed]}


# ---------------------------------------------------------------------------
# Owned channels (creator panel on home page)
# ---------------------------------------------------------------------------

@router.get("/channels")
async def get_owned_channels(
    user: UserDocument = Depends(get_current_user),
    channel_svc: ChannelService = Depends(get_channel_service),
):
    channels = await channel_svc.get_channels_by_owner(user.id)
    return {"channels": channels}
