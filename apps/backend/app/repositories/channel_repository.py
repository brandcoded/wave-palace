"""Data/repository layer for channels.

Two implementations share one interface:
- SeedChannelRepository: in-memory seed data (default, no DB required).
- MongoChannelRepository: PyMongo Async-backed (used when MONGODB_URI is set).
"""

from __future__ import annotations

import copy
import logging
from abc import ABC, abstractmethod

from app.core.config import Settings
from app.seed.channels import SEED_CHANNELS

logger = logging.getLogger("wavepalace.repository")


class ChannelRepository(ABC):
    @abstractmethod
    async def list_channels(self) -> list[dict]:
        """Return all channels (published and unpublished)."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> dict | None:
        """Return a single channel by slug, or None if not found."""

    @abstractmethod
    async def create(self, data: dict) -> dict:
        """Insert a new channel document and return it."""

    @abstractmethod
    async def update(self, slug: str, data: dict) -> dict | None:
        """Merge *data* into the channel with *slug*. Returns updated doc or None."""

    @abstractmethod
    async def delete(self, slug: str) -> bool:
        """Soft-delete: mark deleted=True and unpublish. Returns True if found."""

    @abstractmethod
    async def increment_play_count(self, slug: str) -> bool:
        """Atomically increment playCount. Returns True if channel exists."""

    @abstractmethod
    async def increment_sponsor_impression(self, slug: str) -> bool:
        """Atomically increment sponsor.impressionCount. Returns True if channel exists."""

    @abstractmethod
    async def increment_sponsor_click(self, slug: str) -> bool:
        """Atomically increment sponsor.clickCount. Returns True if channel exists."""


class SeedChannelRepository(ChannelRepository):
    """In-memory repository backed by static seed data (mutable copy)."""

    def __init__(self, channels: list[dict] | None = None) -> None:
        self._channels: list[dict] = copy.deepcopy(
            channels if channels is not None else SEED_CHANNELS
        )

    async def list_channels(self) -> list[dict]:
        return [c for c in self._channels if not c.get("deleted")]

    async def get_by_slug(self, slug: str) -> dict | None:
        return next(
            (c for c in self._channels if c["slug"] == slug and not c.get("deleted")),
            None,
        )

    async def create(self, data: dict) -> dict:
        self._channels.append(data)
        return data

    async def update(self, slug: str, data: dict) -> dict | None:
        for i, c in enumerate(self._channels):
            if c["slug"] == slug:
                self._channels[i] = {**c, **data}
                return self._channels[i]
        return None

    async def delete(self, slug: str) -> bool:
        for i, c in enumerate(self._channels):
            if c["slug"] == slug:
                self._channels[i] = {**c, "isPublished": False, "deleted": True}
                return True
        return False

    async def increment_play_count(self, slug: str) -> bool:
        for i, c in enumerate(self._channels):
            if c["slug"] == slug:
                self._channels[i] = {**c, "playCount": c.get("playCount", 0) + 1}
                return True
        return False

    async def increment_sponsor_impression(self, slug: str) -> bool:
        for i, c in enumerate(self._channels):
            if c["slug"] == slug:
                sp = dict(c.get("sponsor") or {})
                sp["impressionCount"] = sp.get("impressionCount", 0) + 1
                self._channels[i] = {**c, "sponsor": sp}
                return True
        return False

    async def increment_sponsor_click(self, slug: str) -> bool:
        for i, c in enumerate(self._channels):
            if c["slug"] == slug:
                sp = dict(c.get("sponsor") or {})
                sp["clickCount"] = sp.get("clickCount", 0) + 1
                self._channels[i] = {**c, "sponsor": sp}
                return True
        return False


class MongoChannelRepository(ChannelRepository):
    """MongoDB-backed repository using PyMongo Async."""

    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient  # type: ignore

        self._client = AsyncMongoClient(uri)
        self._collection = self._client[database]["channels"]

    async def _ensure_seeded(self) -> None:
        """Populate an empty collection with the base seed channels once.

        Checks the RAW document count (not the deleted-filtered view) so a
        collection where every channel was intentionally deleted is NOT
        re-seeded. Mirrors the self-seeding behaviour of the options repo.
        """
        if await self._collection.count_documents({}, limit=1) == 0:
            await self._collection.insert_many(
                [{**c, "_id": c["id"]} for c in SEED_CHANNELS]
            )
            logger.info("Seeded empty Mongo 'channels' collection with base channels.")

    async def list_channels(self) -> list[dict]:
        await self._ensure_seeded()
        cursor = self._collection.find({"deleted": {"$ne": True}}, {"_id": 0})
        return [doc async for doc in cursor]

    async def get_by_slug(self, slug: str) -> dict | None:
        await self._ensure_seeded()
        return await self._collection.find_one(
            {"slug": slug, "deleted": {"$ne": True}}, {"_id": 0}
        )

    async def create(self, data: dict) -> dict:
        await self._collection.insert_one({**data, "_id": data["id"]})
        return data

    async def update(self, slug: str, data: dict) -> dict | None:
        result = await self._collection.find_one_and_update(
            {"slug": slug},
            {"$set": data},
            return_document=True,
            projection={"_id": 0},
        )
        return result

    async def delete(self, slug: str) -> bool:
        result = await self._collection.delete_many({"slug": slug})
        return result.deleted_count > 0

    async def increment_play_count(self, slug: str) -> bool:
        result = await self._collection.update_one(
            {"slug": slug},
            {"$inc": {"playCount": 1}},
        )
        return result.matched_count > 0

    async def increment_sponsor_impression(self, slug: str) -> bool:
        result = await self._collection.update_one(
            {"slug": slug},
            {"$inc": {"sponsor.impressionCount": 1}},
        )
        return result.matched_count > 0

    async def increment_sponsor_click(self, slug: str) -> bool:
        result = await self._collection.update_one(
            {"slug": slug},
            {"$inc": {"sponsor.clickCount": 1}},
        )
        return result.matched_count > 0


def build_channel_repository(settings: Settings) -> ChannelRepository:
    """Factory: choose Mongo when configured, else fall back to seed mode."""
    if settings.use_seed_mode:
        logger.warning(
            "MONGODB_URI not set — running in LOCAL SEED MODE with in-memory channels."
        )
        return SeedChannelRepository()

    logger.info("Connecting to MongoDB database '%s'.", settings.mongodb_database)
    try:
        return MongoChannelRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:  # pragma: no cover - defensive fallback
        logger.exception("Mongo connection failed — falling back to seed mode.")
        return SeedChannelRepository()
