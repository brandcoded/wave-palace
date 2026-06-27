"""Channel API routes (presentation/transport layer for the backend).

Route handlers stay thin: they parse query params and delegate all rules to
the ChannelService.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.dependencies import get_channel_service, get_follow_service
from app.schemas.channel import Channel
from app.services.channel_service import ChannelService
from app.services.follow_service import FollowService

router = APIRouter(prefix="/api/channels", tags=["channels"])

# Admin-only fields never exposed on the public channel API (Slice 11).
_PUBLIC_EXCLUDE = {"owner_ids", "auto_publish"}


@router.get("", response_model=list[Channel], response_model_exclude=_PUBLIC_EXCLUDE)
async def list_channels(
    genre: str | None = Query(default=None),
    mood: str | None = Query(default=None),
    energy: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    service: ChannelService = Depends(get_channel_service),
) -> list[Channel]:
    return await service.list_published(
        genre=genre, mood=mood, energy=energy, theme=theme
    )


@router.get("/{slug}", response_model=Channel, response_model_exclude=_PUBLIC_EXCLUDE)
async def get_channel(
    slug: str,
    service: ChannelService = Depends(get_channel_service),
) -> Channel:
    channel = await service.get_published_by_slug(slug)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/{slug}/sponsor/impression")
async def record_sponsor_impression(
    slug: str,
    request: Request,
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    ip = request.headers.get("x-forwarded-for", "unknown")
    await service.record_sponsor_impression(slug, ip)
    return {"ok": True}


@router.post("/{slug}/sponsor/click")
async def record_sponsor_click(
    slug: str,
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    await service.record_sponsor_click(slug)
    return {"ok": True}


@router.get("/{slug}/followers/count")
async def get_follower_count(
    slug: str,
    follow_svc: FollowService = Depends(get_follow_service),
) -> dict:
    """Public endpoint — returns the confirmed follower count for a channel."""
    count = await follow_svc.get_follower_count(slug)
    return {"count": count}


@router.post("/{slug}/play")
async def record_play(
    slug: str,
    request: Request,
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    """Increment play count for a channel (fire-and-forget from the web player).

    Rate-limited to one increment per IP+slug per 30 minutes in-process.
    Silently no-ops when the channel doesn't exist in seed mode to avoid 404
    noise from misconfigured players.
    """
    ip = request.headers.get("x-forwarded-for", "unknown")
    ok = await service.record_play(slug, ip)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"ok": True}
