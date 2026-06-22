"""Channel invite service for Slice 11 — Host Onboarding & Ownership.

Admins/music directors generate single-use, 7-day invite links per channel.
A logged-in user accepts an invite to become an owner of that channel. Only a
SHA-256 hash of the raw token is ever persisted; the raw token is returned once
at creation time and never stored.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.repositories.channel_repository import ChannelRepository
from app.repositories.invite_repository import InviteRepository
from app.schemas.channel import Channel
from app.schemas.invite import ChannelInviteToken

_INVITE_TTL_DAYS = 7


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class InviteService:
    def __init__(
        self,
        invite_repo: InviteRepository,
        channel_repo: ChannelRepository,
    ) -> None:
        self._invite_repo = invite_repo
        self._channel_repo = channel_repo

    async def generate_invite(
        self,
        channel_slug: str,
        created_by_user_id: str,
    ) -> tuple[ChannelInviteToken, str]:
        """Create an invite for *channel_slug*. Returns (doc, raw_token).

        The raw token is shown to the admin exactly once — only its hash is stored.
        """
        channel = await self._channel_repo.get_by_slug(channel_slug)
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")

        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        doc = ChannelInviteToken(
            id=str(uuid.uuid4()),
            token_hash=_hash_token(raw_token),
            channel_slug=channel_slug,
            created_by_user_id=created_by_user_id,
            created_at=now,
            expires_at=now + timedelta(days=_INVITE_TTL_DAYS),
        )
        await self._invite_repo.create(doc)
        return doc, raw_token

    async def list_invites(self, channel_slug: str) -> list[ChannelInviteToken]:
        return await self._invite_repo.list_by_channel(channel_slug)

    async def accept_invite(self, raw_token: str, user_id: str) -> Channel:
        """Add *user_id* to the invited channel's owner_ids. Idempotent per user."""
        token_hash = _hash_token(raw_token)
        invite = await self._invite_repo.get_by_token_hash(token_hash)
        if invite is None:
            raise HTTPException(status_code=404, detail="Invite not found")

        if invite.consumed:
            raise HTTPException(status_code=400, detail="This invite has already been used")

        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This invite has expired")

        channel = await self._channel_repo.get_by_slug(invite.channel_slug)
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")

        owner_ids = list(channel.get("owner_ids") or [])
        if user_id not in owner_ids:
            owner_ids.append(user_id)
            await self._channel_repo.update(invite.channel_slug, {"owner_ids": owner_ids})

        await self._invite_repo.consume(token_hash, user_id)

        updated = await self._channel_repo.get_by_slug(invite.channel_slug)
        return Channel.model_validate(updated)
