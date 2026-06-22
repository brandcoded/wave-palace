"""Admin channel management routes."""

from __future__ import annotations

import re
from typing import Any

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_channel_service, get_user_repository
from app.core.auth import get_current_admin
from app.schemas.channel import Channel
from app.schemas.sponsor import Sponsor
from app.schemas.user import UserPublic
from app.services.channel_service import ChannelService
from app.services.url_validator import URLCheckResult, validate_urls

router = APIRouter(prefix="/api/admin/channels", tags=["admin-channels"])

# Fields whose changes require a mux update (VRChat video re-encode).
_OVERLAY_FIELDS = {
    "title", "hostName", "genre", "mood",
    "visualLoopUrl", "coverImageUrl", "playlist",
}


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


class ChannelCreateRequest(BaseModel):
    title: str
    description: str = ""
    genre: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    energy: list[str] = Field(default_factory=list)
    theme: list[str] = Field(default_factory=list)
    hostName: str = ""
    coverImageUrl: str = ""
    visualLoopUrl: str | None = None
    audioUrl: str = ""
    playlist: list[dict] = []
    externalLinks: list[dict] = []
    rightsStatus: str = "owned_or_cleared"
    isPublished: bool = False


class ChannelPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    genre: list[str] | None = None
    mood: list[str] | None = None
    energy: list[str] | None = None
    theme: list[str] | None = None
    hostName: str | None = None
    coverImageUrl: str | None = None
    visualLoopUrl: str | None = None
    audioUrl: str | None = None
    playlist: list[dict] | None = None
    externalLinks: list[dict] | None = None
    rightsStatus: str | None = None
    isPublished: bool | None = None
    streamingActive: bool | None = None
    vrchatFallbackUrl: str | None = None
    owner_ids: list[str] | None = None
    auto_publish: bool | None = None


class StreamingBulkRequest(BaseModel):
    streamingActive: bool


@router.get("", response_model=list[dict])
async def list_all_channels(
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> list[dict]:
    return await service.list_all()


@router.post("", response_model=dict, status_code=201)
async def create_channel(
    body: ChannelCreateRequest,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    import uuid

    slug = _slugify(body.title)
    channel_id = f"channel_{slug.replace('-', '_')}"
    data: dict[str, Any] = {
        "id": channel_id,
        "slug": slug,
        "vrchatPlaybackUrl": "",
        "playCount": 0,
        **body.model_dump(exclude_none=False),
    }
    return await service.create(data)


@router.post("/streaming/bulk", response_model=dict)
async def bulk_set_streaming(
    body: StreamingBulkRequest,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    """Flip streamingActive on all channels at once."""
    channels = await service.list_all()
    count = 0
    for ch in channels:
        updated = await service.update(ch["slug"], {"streamingActive": body.streamingActive})
        if updated is not None:
            count += 1
    return {"updated": count, "streamingActive": body.streamingActive}


@router.patch("/{slug}", response_model=dict)
async def update_channel(
    slug: str,
    body: ChannelPatchRequest,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if patch.keys() & _OVERLAY_FIELDS:
        patch["muxOutdated"] = True
    updated = await service.update(slug, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return updated


@router.delete("/{slug}")
async def delete_channel(
    slug: str,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    deleted = await service.delete(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"ok": True}


@router.patch("/{slug}/sponsor", response_model=dict)
async def update_channel_sponsor(
    slug: str,
    body: Annotated[Sponsor | None, Body()] = None,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> dict:
    sponsor_data = body.model_dump() if body is not None else None
    updated = await service.update(slug, {
        "sponsor": sponsor_data,
        "muxOutdated": True,  # Sponsor text in overlay always requires re-encode
    })
    if updated is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return updated


@router.get("/{slug}/owners", response_model=list[UserPublic])
async def list_channel_owners(
    slug: str,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
    user_repo=Depends(get_user_repository),
) -> list[UserPublic]:
    """Resolve a channel's owner_ids to public user records (Slice 11)."""
    channel = await service.get_raw_by_slug(slug)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    owners: list[UserPublic] = []
    for uid in channel.get("owner_ids") or []:
        user = await user_repo.get(uid)
        if user is not None:
            owners.append(UserPublic(**user.model_dump()))
    return owners


@router.post("/{slug}/validate-urls", response_model=list[URLCheckResult])
async def validate_channel_urls(
    slug: str,
    _: dict = Depends(get_current_admin),
    service: ChannelService = Depends(get_channel_service),
) -> list[URLCheckResult]:
    channels = await service.list_all()
    ch = next((c for c in channels if c.get("slug") == slug), None)
    if ch is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    playlist = ch.get("playlist") or []
    audio_urls: list[str] = []
    for track in playlist:
        if isinstance(track, dict):
            url = track.get("url", "")
        else:
            url = str(track)
        if url:
            audio_urls.append(url)

    visual_loop_url: str | None = ch.get("visualLoopUrl") or None

    return await validate_urls(audio_urls, visual_loop_url)
