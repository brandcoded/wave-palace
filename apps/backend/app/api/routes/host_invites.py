"""Channel invite routes for Slice 11 — Host Onboarding & Ownership.

Two surfaces share this file:
- Admin/music-director: generate + list invite links for a channel.
- Authenticated user: accept an invite to become a channel owner.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_invite_service
from app.core.auth import get_current_user, require_roles
from app.schemas.invite import ChannelInvitePublic
from app.schemas.user import UserDocument
from app.services.invite_service import InviteService

router = APIRouter(tags=["host-invites"])


def _frontend_base() -> str:
    origin = os.getenv("FRONTEND_ORIGIN", "https://wavepalace.live")
    # FRONTEND_ORIGIN may be a comma-separated list; use the first entry.
    return origin.split(",")[0].strip().rstrip("/")


class InviteCreateResponse(BaseModel):
    invite_url: str
    expires_at: str
    channel_slug: str


class InviteAcceptRequest(BaseModel):
    token: str


class InviteAcceptResponse(BaseModel):
    channel_slug: str
    channel_title: str
    message: str


@router.post(
    "/api/admin/channels/{slug}/invites",
    response_model=InviteCreateResponse,
    status_code=201,
)
async def create_channel_invite(
    slug: str,
    user: UserDocument = Depends(require_roles("admin", "music_director")),
    service: InviteService = Depends(get_invite_service),
) -> InviteCreateResponse:
    doc, raw_token = await service.generate_invite(slug, user.id)
    return InviteCreateResponse(
        invite_url=f"{_frontend_base()}/host/join?token={raw_token}",
        expires_at=doc.expires_at.isoformat(),
        channel_slug=slug,
    )


@router.get(
    "/api/admin/channels/{slug}/invites",
    response_model=list[ChannelInvitePublic],
)
async def list_channel_invites(
    slug: str,
    _: UserDocument = Depends(require_roles("admin", "music_director")),
    service: InviteService = Depends(get_invite_service),
) -> list[ChannelInvitePublic]:
    invites = await service.list_invites(slug)
    return [ChannelInvitePublic(**i.model_dump()) for i in invites]


@router.post("/api/host/invite/accept", response_model=InviteAcceptResponse)
async def accept_channel_invite(
    body: InviteAcceptRequest,
    user: UserDocument = Depends(get_current_user),
    service: InviteService = Depends(get_invite_service),
) -> InviteAcceptResponse:
    channel = await service.accept_invite(body.token, user.id)
    return InviteAcceptResponse(
        channel_slug=channel.slug,
        channel_title=channel.title,
        message=f"You are now a host of {channel.title}.",
    )
