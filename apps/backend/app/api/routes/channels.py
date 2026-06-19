"""Channel API routes (presentation/transport layer for the backend).

Route handlers stay thin: they parse query params and delegate all rules to
the ChannelService.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.dependencies import get_channel_service
from app.schemas.channel import Channel
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("", response_model=list[Channel])
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


@router.get("/{slug}", response_model=Channel)
async def get_channel(
    slug: str,
    service: ChannelService = Depends(get_channel_service),
) -> Channel:
    channel = await service.get_published_by_slug(slug)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


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
