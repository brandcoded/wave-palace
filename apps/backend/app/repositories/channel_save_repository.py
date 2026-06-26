"""Repository layer for Slice 12 — saved channels."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.me import ChannelSaveDocument

logger = logging.getLogger("wavepalace.channel_saves")


class ChannelSaveRepository(ABC):
    @abstractmethod
    async def save(self, user_id: str, channel_slug: str) -> None: ...

    @abstractmethod
    async def unsave(self, user_id: str, channel_slug: str) -> None: ...

    @abstractmethod
    async def is_saved(self, user_id: str, channel_slug: str) -> bool: ...

    @abstractmethod
    async def get_saved_slugs(self, user_id: str) -> list[str]: ...


class SeedChannelSaveRepository(ChannelSaveRepository):
    def __init__(self) -> None:
        self._saves: list[ChannelSaveDocument] = []

    async def save(self, user_id: str, channel_slug: str) -> None:
        if await self.is_saved(user_id, channel_slug):
            return
        self._saves.append(ChannelSaveDocument(
            id=str(uuid.uuid4()),
            user_id=user_id,
            channel_slug=channel_slug,
            saved_at=datetime.now(timezone.utc),
        ))

    async def unsave(self, user_id: str, channel_slug: str) -> None:
        self._saves = [
            s for s in self._saves
            if not (s.user_id == user_id and s.channel_slug == channel_slug)
        ]

    async def is_saved(self, user_id: str, channel_slug: str) -> bool:
        return any(s.user_id == user_id and s.channel_slug == channel_slug for s in self._saves)

    async def get_saved_slugs(self, user_id: str) -> list[str]:
        saves = [s for s in self._saves if s.user_id == user_id]
        saves.sort(key=lambda s: s.saved_at, reverse=True)
        return [s.channel_slug for s in saves]


class MongoChannelSaveRepository(ChannelSaveRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["channel_saves"]

    async def save(self, user_id: str, channel_slug: str) -> None:
        await self._col.update_one(
            {"user_id": user_id, "channel_slug": channel_slug},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "channel_slug": channel_slug,
                "saved_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    async def unsave(self, user_id: str, channel_slug: str) -> None:
        await self._col.delete_one({"user_id": user_id, "channel_slug": channel_slug})

    async def is_saved(self, user_id: str, channel_slug: str) -> bool:
        return await self._col.find_one({"user_id": user_id, "channel_slug": channel_slug}) is not None

    async def get_saved_slugs(self, user_id: str) -> list[str]:
        cursor = self._col.find(
            {"user_id": user_id}, {"channel_slug": 1, "_id": 0}
        ).sort("saved_at", -1)
        return [d["channel_slug"] async for d in cursor]


def build_channel_save_repository(settings) -> ChannelSaveRepository:
    if settings.use_seed_mode:
        return SeedChannelSaveRepository()
    try:
        return MongoChannelSaveRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo channel-save repo failed — falling back to seed mode.")
        return SeedChannelSaveRepository()
