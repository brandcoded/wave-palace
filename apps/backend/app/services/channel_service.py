"""Business/service layer for channels."""

from __future__ import annotations

import time

from app.repositories.channel_repository import ChannelRepository
from app.schemas.channel import Channel

# In-memory TTL cache for play-count rate limiting: {slug:ip -> timestamp}
_PLAY_CACHE: dict[str, float] = {}
_PLAY_TTL = 1800  # 30 minutes


class ChannelService:
    def __init__(self, repository: ChannelRepository) -> None:
        self._repository = repository

    # ------------------------------------------------------------------
    # Public read
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid(channel: dict) -> bool:
        return bool(channel.get("audioUrl")) and bool(channel.get("vrchatPlaybackUrl"))

    @staticmethod
    def _matches(channel: dict, field: str, value: str | None) -> bool:
        if not value:
            return True
        return str(channel.get(field, "")).strip().lower() == value.strip().lower()

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
            result.append(Channel.model_validate(c))
        return result

    async def get_published_by_slug(self, slug: str) -> Channel | None:
        channel = await self._repository.get_by_slug(slug)
        if not channel or not channel.get("isPublished") or not self._is_valid(channel):
            return None
        return Channel.model_validate(channel)

    # ------------------------------------------------------------------
    # Admin write
    # ------------------------------------------------------------------

    async def list_all(self) -> list[dict]:
        return await self._repository.list_channels()

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
