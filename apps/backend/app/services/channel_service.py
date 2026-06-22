"""Business/service layer for channels."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from app.repositories.channel_repository import ChannelRepository
from app.schemas.channel import Channel
from app.schemas.sponsor import Sponsor, sponsor_is_live

# In-memory TTL cache for play-count rate limiting: {slug:ip -> timestamp}
_PLAY_CACHE: dict[str, float] = {}
_PLAY_TTL = 1800  # 30 minutes

# In-memory TTL cache for sponsor impression rate limiting: {slug:ip -> timestamp}
_IMPRESSION_CACHE: dict[str, float] = {}


class ChannelService:
    def __init__(self, repository: ChannelRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------
    # Public read
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid(channel: dict) -> bool:
        return bool(channel.get("audioUrl"))

    @staticmethod
    def _matches(channel: dict, field: str, value: str | None) -> bool:
        if not value:
            return True
        target = value.strip().lower()
        field_val = channel.get(field, "")
        if isinstance(field_val, list):
            return any(str(v).strip().lower() == target for v in field_val)
        return str(field_val).strip().lower() == target

    @staticmethod
    def _with_live_sponsor(channel: Channel) -> Channel:
        """Strip sponsor from the public response unless it is currently live."""
        if channel.sponsor is not None and not sponsor_is_live(channel.sponsor):
            return channel.model_copy(update={"sponsor": None})
        return channel

    async def list_published(
        self,
        genre: str | None = None,
        mood: str | None = None,
        energy: str | None = None,
        theme: str | None = None,
    ) -> list[Channel]:
        channels = await self._repository.list_channels()
        result: list[Channel] = []
        for c in channels:
            if not c.get("isPublished"):
                continue
            if not self._is_valid(c):
                continue
            if not self._matches(c, "genre", genre):
                continue
            if not self._matches(c, "mood", mood):
                continue
            if not self._matches(c, "energy", energy):
                continue
            if not self._matches(c, "theme", theme):
                continue
            result.append(self._with_live_sponsor(Channel.model_validate(c)))
        return result

    async def get_published_by_slug(self, slug: str) -> Channel | None:
        channel = await self._repository.get_by_slug(slug)
        if not channel or not channel.get("isPublished") or not self._is_valid(channel):
            return None
        return self._with_live_sponsor(Channel.model_validate(channel))

    # ------------------------------------------------------------------
    # Admin write
    # ------------------------------------------------------------------

    async def list_all(self) -> list[dict]:
        return await self._repository.list_channels()

    async def get_raw_by_slug(self, slug: str) -> dict | None:
        """Return the raw channel dict regardless of published state (admin/host use)."""
        return await self._repository.get_by_slug(slug)

    async def get_channels_by_owner(self, user_id: str) -> list[dict]:
        return await self._repository.get_channels_by_owner(user_id)

    async def create(self, data: dict) -> dict:
        return await self._repository.create(data)

    async def update(self, slug: str, data: dict) -> dict | None:
        return await self._repository.update(slug, data)

    async def delete(self, slug: str) -> bool:
        return await self._repository.delete(slug)

    # ------------------------------------------------------------------
    # Play count
    # ------------------------------------------------------------------

    async def record_play(self, slug: str, ip: str) -> bool:
        """Increment play count unless this IP already played this channel recently."""
        channel = await self._repository.get_by_slug(slug)
        if channel is None:
            return False

        key = f"{slug}:{ip}"
        now = time.time()
        last = _PLAY_CACHE.get(key, 0.0)
        if now - last < _PLAY_TTL:
            return True  # already counted recently — no-op but not an error

        _PLAY_CACHE[key] = now
        # Evict stale entries occasionally to bound memory usage.
        if len(_PLAY_CACHE) > 10_000:
            cutoff = now - _PLAY_TTL
            stale = [k for k, v in _PLAY_CACHE.items() if v < cutoff]
            for k in stale:
                _PLAY_CACHE.pop(k, None)

        await self._repository.increment_play_count(slug)
        return True

    # ------------------------------------------------------------------
    # Sponsor events
    # ------------------------------------------------------------------

    async def _channel_has_live_sponsor(self, slug: str) -> bool:
        channel = await self._repository.get_by_slug(slug)
        if channel is None:
            return False
        raw_sponsor = channel.get("sponsor")
        if not raw_sponsor:
            return False
        sp = Sponsor.model_validate(raw_sponsor)
        return sponsor_is_live(sp, datetime.now(timezone.utc))

    async def record_sponsor_impression(self, slug: str, ip: str) -> bool:
        """Increment sponsor impressionCount (rate-limited by IP+slug, 30-min TTL)."""
        if not await self._channel_has_live_sponsor(slug):
            return True  # silent no-op

        key = f"imp:{slug}:{ip}"
        now = time.time()
        if now - _IMPRESSION_CACHE.get(key, 0.0) < _PLAY_TTL:
            return True  # already counted recently

        _IMPRESSION_CACHE[key] = now
        if len(_IMPRESSION_CACHE) > 10_000:
            cutoff = now - _PLAY_TTL
            stale = [k for k, v in _IMPRESSION_CACHE.items() if v < cutoff]
            for k in stale:
                _IMPRESSION_CACHE.pop(k, None)

        await self._repository.increment_sponsor_impression(slug)
        return True

    async def record_sponsor_click(self, slug: str) -> bool:
        """Increment sponsor clickCount (no rate limit — intentional user action)."""
        if not await self._channel_has_live_sponsor(slug):
            return True  # silent no-op
        await self._repository.increment_sponsor_click(slug)
        return True
