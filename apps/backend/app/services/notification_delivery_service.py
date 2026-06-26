"""Notification delivery service for Slice 13.

Dispatches email (Resend) and Discord bot DMs in response to content-change events.
All methods are fire-and-forget: callers wrap them in asyncio.create_task.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import Settings
from app.repositories.follow_repository import FollowRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.throttle_repository import ThrottleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.follow import FollowDocument
from app.schemas.me import NotificationCreate
from app.services.email_templates import (
    channel_live_email,
    new_tracks_email,
    weekly_digest_email,
)
from app.services.listen_history_service import ListenHistoryService

logger = logging.getLogger("wavepalace.notification_delivery")

_THROTTLE_NEW_TRACKS_H = 24.0
_THROTTLE_CHANNEL_LIVE_H = 2.0
_THROTTLE_DIGEST_H = 144.0  # 6 days


class NotificationDeliveryService:
    def __init__(
        self,
        follow_repo: FollowRepository,
        notif_repo: NotificationRepository,
        throttle_repo: ThrottleRepository,
        user_repo: UserRepository,
        listen_history_svc: ListenHistoryService,
        settings: Settings,
    ) -> None:
        self._follows = follow_repo
        self._notifs = notif_repo
        self._throttle = throttle_repo
        self._users = user_repo
        self._history_svc = listen_history_svc
        self._settings = settings

    def _frontend_origin(self) -> str:
        return self._settings.frontend_origin.split(",")[0].strip()

    def _unsubscribe_url(self, follow_id: str) -> str:
        return f"{self._frontend_origin()}/follows?unsubscribe={follow_id}"

    async def _follow_identity_key(self, follow: FollowDocument) -> str:
        """Return a throttle/identity key for this follow (user_id or synthetic)."""
        if follow.discord_user_id:
            user = await self._users.get_by_discord_id(follow.discord_user_id)
            if user:
                return user.id
        if follow.email:
            user = await self._users.get_by_email(follow.email)
            if user:
                return user.id
        return f"follow:{follow.id}"

    async def _inbox_user_id(self, follow: FollowDocument) -> str | None:
        """Return the UserDocument.id for inbox notifications, or None if no account."""
        if follow.discord_user_id:
            user = await self._users.get_by_discord_id(follow.discord_user_id)
            if user:
                return user.id
        if follow.email:
            user = await self._users.get_by_email(follow.email)
            if user:
                return user.id
        return None

    # -------------------------------------------------------------------------
    # Public delivery methods
    # -------------------------------------------------------------------------

    async def notify_new_tracks(
        self,
        channel_slug: str,
        channel_name: str,
        new_tracks: list[dict],
        channel_url: str,
        vrchat_url: str | None = None,
        ignore_throttle: bool = False,
    ) -> dict:
        """Deliver new-track notifications to all confirmed follows for a channel."""
        follows = await self._follows.get_by_channel(channel_slug)
        sent = skipped = 0

        for follow in follows:
            if not follow.confirmed or not follow.notify_new_tracks:
                skipped += 1
                continue

            identity_key = await self._follow_identity_key(follow)

            if not ignore_throttle and await self._throttle.is_throttled(
                identity_key, channel_slug, "new_tracks", _THROTTLE_NEW_TRACKS_H
            ):
                skipped += 1
                continue

            ok = await self._deliver_follow(
                follow=follow,
                channel_slug=channel_slug,
                channel_name=channel_name,
                notif_type="new_tracks",
                notif_body=f"{len(new_tracks)} new track(s) added to {channel_name}",
                new_tracks=new_tracks,
                channel_url=channel_url,
                vrchat_url=vrchat_url,
            )
            if ok:
                await self._throttle.record_sent(identity_key, channel_slug, "new_tracks")
                sent += 1
            else:
                skipped += 1

        logger.info("notify_new_tracks %s: sent=%d skipped=%d", channel_slug, sent, skipped)
        return {"sent": sent, "skipped": skipped}

    async def notify_channel_live(
        self,
        channel_slug: str,
        channel_name: str,
        channel_url: str,
        vrchat_url: str | None = None,
        ignore_throttle: bool = False,
    ) -> dict:
        # TODO: called from Slice 4 live event route
        follows = await self._follows.get_by_channel(channel_slug)
        sent = skipped = 0

        for follow in follows:
            if not follow.confirmed or not follow.notify_channel_live:
                skipped += 1
                continue

            identity_key = await self._follow_identity_key(follow)

            if not ignore_throttle and await self._throttle.is_throttled(
                identity_key, channel_slug, "channel_live", _THROTTLE_CHANNEL_LIVE_H
            ):
                skipped += 1
                continue

            ok = await self._deliver_follow(
                follow=follow,
                channel_slug=channel_slug,
                channel_name=channel_name,
                notif_type="channel_live",
                notif_body=f"{channel_name} is live now!",
                new_tracks=[],
                channel_url=channel_url,
                vrchat_url=vrchat_url,
            )
            if ok:
                await self._throttle.record_sent(identity_key, channel_slug, "channel_live")
                sent += 1
            else:
                skipped += 1

        return {"sent": sent, "skipped": skipped}

    async def send_weekly_digest(self) -> dict:
        """Send digest emails to all follows with notify_digest=True."""
        all_follows = await self._follows.get_all_follows()
        digest_follows = [f for f in all_follows if f.notify_digest]

        # Group by email, resolving discord follows to account email if possible
        email_map: dict[str, list[FollowDocument]] = {}
        for follow in digest_follows:
            email = follow.email
            if not email and follow.discord_user_id:
                user = await self._users.get_by_discord_id(follow.discord_user_id)
                if user and user.email:
                    email = user.email
            if email:
                email_map.setdefault(email, []).append(follow)

        sent = skipped = 0
        for email, follows in email_map.items():
            # Use the first follow as representative for throttle key
            rep = follows[0]
            identity_key = await self._follow_identity_key(rep)

            if await self._throttle.is_throttled(identity_key, "", "digest", _THROTTLE_DIGEST_H):
                skipped += 1
                continue

            # Build content
            followed_channels = [
                {"name": f.channel_slug, "url": f"{self._frontend_origin()}/channels/{f.channel_slug}"}
                for f in follows
            ]

            # Get listen history if user account exists
            recent_channels: list[str] = []
            user_id: str | None = None
            user = await self._users.get_by_email(email)
            if user:
                user_id = user.id
                try:
                    history = await self._history_svc.get_history(user.id)
                    top = history.get("top_channel")
                    if top:
                        recent_channels.append(top)
                    last = history.get("last_channel")
                    if last and last != top:
                        recent_channels.append(last)
                except Exception:
                    pass

            unsubscribe_url = self._unsubscribe_url(rep.id)
            subject, html, text = weekly_digest_email(
                recent_channels=recent_channels,
                followed_channels=followed_channels,
                unsubscribe_url=unsubscribe_url,
            )

            ok = await _send_resend_email(
                api_key=self._settings.resend_api_key,
                to=email,
                subject=subject,
                html=html,
                text=text,
            )
            if ok:
                await self._throttle.record_sent(identity_key, "", "digest")
                if user_id:
                    await self._notifs.create(
                        NotificationCreate(
                            user_id=user_id,
                            type="digest",
                            title="Your weekly WavePalace digest",
                            body="Check out what's new on your followed channels.",
                            channel_slug=None,
                        )
                    )
                sent += 1
            else:
                skipped += 1

        logger.info("send_weekly_digest: sent=%d skipped=%d", sent, skipped)
        return {"sent": sent, "skipped": skipped}

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _deliver_follow(
        self,
        follow: FollowDocument,
        channel_slug: str,
        channel_name: str,
        notif_type: str,
        notif_body: str,
        new_tracks: list[dict],
        channel_url: str,
        vrchat_url: str | None,
    ) -> bool:
        unsubscribe_url = self._unsubscribe_url(follow.id)
        ok = False

        if follow.notification_channel == "email" and follow.email:
            if notif_type == "new_tracks":
                subject, html, text = new_tracks_email(
                    channel_name=channel_name,
                    tracks=new_tracks,
                    channel_url=channel_url,
                    vrchat_url=vrchat_url,
                    unsubscribe_url=unsubscribe_url,
                )
            else:
                subject, html, text = channel_live_email(
                    channel_name=channel_name,
                    channel_url=channel_url,
                    vrchat_url=vrchat_url,
                    unsubscribe_url=unsubscribe_url,
                )
            ok = await _send_resend_email(
                api_key=self._settings.resend_api_key,
                to=follow.email,
                subject=subject,
                html=html,
                text=text,
            )

        elif follow.notification_channel == "discord" and follow.discord_user_id:
            if notif_type == "new_tracks":
                msg = f"**{channel_name}** — {len(new_tracks)} new track(s) added!\n{channel_url}"
            else:
                msg = f"**{channel_name}** is live now!\n{channel_url}"
            ok = await _send_discord_dm(
                bot_token=self._settings.discord_bot_token,
                discord_user_id=follow.discord_user_id,
                message=msg,
            )

        if ok:
            # Create inbox notification for registered users
            user_id = await self._inbox_user_id(follow)
            if user_id:
                try:
                    await self._notifs.create(
                        NotificationCreate(
                            user_id=user_id,
                            type=notif_type,  # type: ignore[arg-type]
                            title=f"New on {channel_name}" if notif_type == "new_tracks" else f"{channel_name} is live!",
                            body=notif_body,
                            channel_slug=channel_slug,
                        )
                    )
                except Exception:
                    logger.exception("Failed to create inbox notification for user %s", user_id)

        return ok


# ---------------------------------------------------------------------------
# Low-level send helpers (module-level so they can be tested in isolation)
# ---------------------------------------------------------------------------

async def _send_resend_email(
    api_key: str | None,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> bool:
    if not api_key:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "noreply@wavepalace.live",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
        if resp.status_code >= 400:
            logger.error("Resend error %d for %s: %s", resp.status_code, to, resp.text)
            return False
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


async def _send_discord_dm(
    bot_token: str | None,
    discord_user_id: str,
    message: str,
) -> bool:
    if not bot_token:
        logger.warning("DISCORD_BOT_TOKEN not set — skipping DM to %s", discord_user_id)
        return False
    try:
        import httpx
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            # Create or fetch DM channel
            dm_resp = await client.post(
                "https://discord.com/api/v10/users/@me/channels",
                headers=headers,
                json={"recipient_id": discord_user_id},
            )
            if dm_resp.status_code >= 400:
                logger.error("Discord create DM error %d: %s", dm_resp.status_code, dm_resp.text)
                return False
            channel_id = dm_resp.json()["id"]

            # Send message
            msg_resp = await client.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=headers,
                json={"content": message},
            )
            if msg_resp.status_code >= 400:
                logger.error("Discord send message error %d: %s", msg_resp.status_code, msg_resp.text)
                return False
        return True
    except Exception:
        logger.exception("Failed to send Discord DM to %s", discord_user_id)
        return False
