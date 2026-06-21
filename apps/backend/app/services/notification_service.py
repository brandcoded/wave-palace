"""Fan-out notification service for Slice 9.

SMS raises NotImplementedError — A2P 10DLC carrier registration and TCPA
compliance required before enabling. All external calls are no-ops when the
relevant env var (DISCORD_BOT_TOKEN, VAPID_PRIVATE_KEY, RESEND_API_KEY) is absent.
"""

from __future__ import annotations

import logging
import os

from app.repositories.follow_repository import FollowRepository

logger = logging.getLogger("wavepalace.notifications")


class NotificationService:
    def __init__(self, follow_repo: FollowRepository) -> None:
        self._follow_repo = follow_repo

    async def notify_channel_going_live(self, channel_slug: str) -> None:
        follows = await self._follow_repo.get_by_channel(channel_slug)
        for f in follows:
            if f.notification_channel == "discord" and f.discord_user_id:
                await self._send_discord_dm(
                    f.discord_user_id,
                    f"🎵 {channel_slug} is now live on WavePalace! Listen at wavepalace.live",
                )
            elif f.notification_channel == "browser_push" and f.push_subscription:
                await self._send_web_push(
                    f.push_subscription,
                    {"title": "WavePalace is live!", "body": channel_slug},
                )
            elif f.notification_channel == "email" and f.email and f.confirmed:
                await self._send_email(
                    f.email,
                    f"{channel_slug} is live on WavePalace",
                    f"<p>{channel_slug} is now live. Listen at wavepalace.live</p>",
                )

    async def notify_event_announced(self, channel_slug: str, event_name: str) -> None:
        follows = await self._follow_repo.get_by_channel(channel_slug)
        for f in follows:
            if f.notification_channel == "discord" and f.discord_user_id:
                await self._send_discord_dm(
                    f.discord_user_id,
                    f"🎉 New event on {channel_slug}: {event_name}",
                )

    async def notify_new_guest_dj(self, channel_slug: str, dj_name: str) -> None:
        follows = await self._follow_repo.get_by_channel(channel_slug)
        for f in follows:
            if f.notification_channel == "discord" and f.discord_user_id:
                await self._send_discord_dm(
                    f.discord_user_id,
                    f"🎧 Guest DJ on {channel_slug}: {dj_name}",
                )

    async def _send_discord_dm(self, discord_user_id: str, message: str) -> None:
        bot_token = os.getenv("DISCORD_BOT_TOKEN")
        if not bot_token:
            logger.warning("DISCORD_BOT_TOKEN not set — skipping DM to %s", discord_user_id)
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json",
                }
                dm = await client.post(
                    "https://discord.com/api/users/@me/channels",
                    headers=headers,
                    json={"recipient_id": discord_user_id},
                )
                if dm.status_code not in (200, 201):
                    logger.warning(
                        "Could not open DM channel for %s: %s", discord_user_id, dm.text
                    )
                    return
                channel_id = dm.json()["id"]
                await client.post(
                    f"https://discord.com/api/channels/{channel_id}/messages",
                    headers=headers,
                    json={"content": message},
                )
        except Exception:
            logger.exception("Failed to send Discord DM to %s", discord_user_id)

    async def _send_web_push(self, push_subscription: dict, payload: dict) -> None:
        vapid_private = os.getenv("VAPID_PRIVATE_KEY")
        if not vapid_private:
            logger.warning("VAPID_PRIVATE_KEY not set — skipping web push")
            return
        try:
            import json as _json
            from pywebpush import webpush  # type: ignore[import]
            webpush(
                subscription_info=push_subscription,
                data=_json.dumps(payload),
                vapid_private_key=vapid_private,
                vapid_claims={"sub": "mailto:noreply@wavepalace.live"},
            )
        except Exception:
            logger.exception("Web push failed — subscription may be stale")

    async def _send_email(self, email: str, subject: str, body_html: str) -> None:
        api_key = os.getenv("RESEND_API_KEY")
        if not api_key:
            logger.warning("RESEND_API_KEY not set — skipping email to %s", email)
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
                        "subject": subject,
                        "html": body_html,
                    },
                )
        except Exception:
            logger.exception("Failed to send email to %s", email)

    async def _send_sms(self, phone: str, message: str) -> None:
        # SMS delivery is not enabled in this build.
        # A2P 10DLC carrier registration and TCPA compliance required before enabling.
        # Use Discord or browser push for live alerts.
        raise NotImplementedError("SMS delivery is not enabled in this build.")
