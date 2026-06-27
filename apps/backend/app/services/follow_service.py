"""Follow intent submission and management for Slice 9."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException

from app.repositories.channel_repository import ChannelRepository
from app.repositories.code_repository import CodeRepository
from app.repositories.follow_repository import FollowRepository
from app.schemas.code import CodeDocument
from app.schemas.follow import (
    FollowDocument,
    FollowPublicView,
    FollowResponse,
    FollowSubmitRequest,
)

logger = logging.getLogger("wavepalace.follows")

_TOKEN_TTL_HOURS = 24
_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")


def make_confirm_token(follow_id: str, email: str) -> str:
    """Generate a signed email-confirmation JWT (exported for tests)."""
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    return jwt.encode(
        {"follow_id": follow_id, "email": email, "type": "email_confirm", "exp": exp},
        _jwt_secret(),
        algorithm=_ALGORITHM,
    )


def _decode_confirm_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
        if payload.get("type") != "email_confirm":
            raise ValueError("Wrong token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Confirmation link has expired")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid confirmation link")


class FollowService:
    def __init__(
        self,
        follow_repo: FollowRepository,
        code_repo: CodeRepository,
        channel_repo: ChannelRepository,
    ) -> None:
        self._follow_repo = follow_repo
        self._code_repo = code_repo
        self._channel_repo = channel_repo

    async def _resolve_active_code(self, code: str) -> CodeDocument:
        doc = await self._code_repo.get(code.upper())
        if doc is None or not doc.active:
            raise HTTPException(
                status_code=404,
                detail="This code is no longer active — tune in at wavepalace.live",
            )
        now = datetime.now(tz=timezone.utc)
        if doc.expires_at:
            exp = doc.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                raise HTTPException(
                    status_code=404,
                    detail="This code is no longer active — tune in at wavepalace.live",
                )
        return doc

    async def submit_follow(
        self,
        code: str,
        request: FollowSubmitRequest,
        frontend_base: str = "https://wavepalace.live",
    ) -> FollowResponse:
        code_doc = await self._resolve_active_code(code)

        duplicate = await self._follow_repo.exists(
            entity_id=code_doc.entity_id,
            notification_channel=request.channel,
            discord_user_id=request.discord_user_id,
            email=request.email,
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="You're already following this channel.")

        confirmed = request.channel in ("discord", "browser_push")
        follow_id = str(uuid4())

        doc = FollowDocument(
            id=follow_id,
            entity_type=code_doc.entity_type,
            entity_id=code_doc.entity_id,
            channel_slug=code_doc.channel_slug,
            notification_channel=request.channel,
            discord_user_id=request.discord_user_id,
            discord_username=request.discord_username,
            email=request.email,
            push_subscription=request.push_subscription,
            vrchat_username=request.vrchat_username,
            confirmed=confirmed,
            created_at=datetime.now(tz=timezone.utc),
            code_used=code.upper(),
        )
        await self._follow_repo.create(doc)

        if request.channel == "email" and request.email:
            token = make_confirm_token(follow_id, request.email)
            confirm_url = f"{frontend_base}/follow/confirm?token={token}"
            await _send_confirm_email(request.email, confirm_url)

        return FollowResponse(follow_id=follow_id, channel=request.channel, confirmed=confirmed)

    async def confirm_email(self, token: str) -> FollowDocument:
        payload = _decode_confirm_token(token)
        follow_id = payload["follow_id"]
        updated = await self._follow_repo.update(follow_id, {"confirmed": True})
        if updated is None:
            raise HTTPException(status_code=404, detail="Follow not found")
        return updated

    async def get_listener_follows(
        self,
        discord_user_id: str | None,
        email: str | None,
    ) -> list[FollowPublicView]:
        follows = await self._follow_repo.get_by_identity(discord_user_id, email)
        result = []
        for f in follows:
            channel = await self._channel_repo.get_by_slug(f.channel_slug)
            display_name = channel.get("title", f.channel_slug) if channel else f.channel_slug
            ch_created_at = channel.get("created_at") if channel else None
            result.append(
                FollowPublicView(
                    id=f.id,
                    entity_type=f.entity_type,
                    channel_slug=f.channel_slug,
                    display_name=display_name,
                    notification_channel=f.notification_channel,
                    confirmed=f.confirmed,
                    created_at=f.created_at,
                    notify_new_tracks=f.notify_new_tracks,
                    notify_channel_live=f.notify_channel_live,
                    notify_digest=f.notify_digest,
                    channel_created_at=ch_created_at,
                )
            )
        return result

    async def update_follow(
        self,
        follow_id: str,
        discord_user_id: str | None,
        email: str | None,
        updates: dict,
    ) -> FollowPublicView:
        _ALLOWED = {"notification_channel", "notify_new_tracks", "notify_channel_live", "notify_digest"}
        safe_updates = {k: v for k, v in updates.items() if k in _ALLOWED}
        if not safe_updates:
            raise HTTPException(status_code=422, detail="No updatable fields provided")
        doc = await self._follow_repo.get(follow_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Follow not found")
        owns = (discord_user_id is not None and doc.discord_user_id == discord_user_id) or (
            email is not None and doc.email == email
        )
        if not owns:
            raise HTTPException(status_code=404, detail="Follow not found")
        updated = await self._follow_repo.update(follow_id, safe_updates)
        channel = await self._channel_repo.get_by_slug(updated.channel_slug)
        display_name = channel.get("title", updated.channel_slug) if channel else updated.channel_slug
        return FollowPublicView(
            id=updated.id,
            entity_type=updated.entity_type,
            channel_slug=updated.channel_slug,
            display_name=display_name,
            notification_channel=updated.notification_channel,
            confirmed=updated.confirmed,
            created_at=updated.created_at,
            notify_new_tracks=updated.notify_new_tracks,
            notify_channel_live=updated.notify_channel_live,
            notify_digest=updated.notify_digest,
        )

    async def follow_as_user(
        self,
        code: str,
        user: "UserDocument",
    ) -> FollowResponse:
        from app.schemas.user import UserDocument as _UD  # local import to avoid circular

        code_doc = await self._resolve_active_code(code)

        # Prefer discord when available (instant confirm, no email confirmation loop)
        if user.discord_user_id:
            nc = "discord"
            discord_user_id = user.discord_user_id
            email = None
        elif user.email:
            nc = "email"
            discord_user_id = None
            email = user.email
        else:
            raise HTTPException(status_code=422, detail="Account has no email or Discord linked.")

        duplicate = await self._follow_repo.exists(
            entity_id=code_doc.entity_id,
            notification_channel=nc,
            discord_user_id=discord_user_id,
            email=email,
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="You're already following this channel.")

        from uuid import uuid4
        from datetime import datetime, timezone

        follow_id = str(uuid4())
        doc = FollowDocument(
            id=follow_id,
            entity_type=code_doc.entity_type,
            entity_id=code_doc.entity_id,
            channel_slug=code_doc.channel_slug,
            notification_channel=nc,
            discord_user_id=discord_user_id,
            discord_username=None,
            email=email,
            confirmed=True,
            created_at=datetime.now(tz=timezone.utc),
            code_used=code.upper(),
        )
        await self._follow_repo.create(doc)
        return FollowResponse(follow_id=follow_id, channel=nc, confirmed=True)

    async def get_follow_status(self, user: "UserDocument", channel_slug: str) -> dict:
        follow = await self._follow_repo.get_by_user_and_channel(
            discord_user_id=user.discord_user_id,
            email=user.email,
            channel_slug=channel_slug,
        )
        if follow and follow.confirmed:
            return {"following": True, "follow_id": str(follow.id)}
        return {"following": False, "follow_id": None}

    async def get_follower_count(self, channel_slug: str) -> int:
        return await self._follow_repo.count_confirmed_by_channel(channel_slug)

    async def delete_follow(
        self,
        follow_id: str,
        discord_user_id: str | None,
        email: str | None,
    ) -> None:
        doc = await self._follow_repo.get(follow_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Follow not found")
        owns = (discord_user_id is not None and doc.discord_user_id == discord_user_id) or (
            email is not None and doc.email == email
        )
        if not owns:
            raise HTTPException(status_code=404, detail="Follow not found")
        await self._follow_repo.delete(follow_id)


async def _send_confirm_email(email: str, confirm_url: str) -> None:
    """Send Resend double opt-in email. No-op if RESEND_API_KEY not set."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — skipping confirmation email to %s", email)
        return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "noreply@wavepalace.live",
                    "to": [email],
                    "subject": "Confirm your WavePalace follow",
                    "html": (
                        f"<p>Click to confirm your WavePalace follow: "
                        f'<a href="{confirm_url}">{confirm_url}</a></p>'
                    ),
                },
            )
    except Exception:
        logger.exception("Failed to send confirmation email to %s", email)
