"""Business/service layer for channels.

Holds the rules that are NOT data access and NOT presentation:
- only published channels are exposed publicly
- optional filtering by genre / mood / energy / theme (case-insensitive)
- validation that required playback URLs exist
"""

from __future__ import annotations

from app.repositories.channel_repository import ChannelRepository
from app.schemas.channel import Channel


class ChannelService:
    def __init__(self, repository: ChannelRepository) -> None:
        self._repository = repository

    @staticmethod
    def _is_valid(channel: dict) -> bool:
        """Audio URL and VRChat URL must be present for a channel to be served."""
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
