"""Data/repository layer for channels.

Two implementations share one interface:
- SeedChannelRepository: in-memory seed data (default, no DB required).
- MongoChannelRepository: PyMongo Async-backed (used when MONGODB_URI is set).

The service layer depends only on the abstract interface, so swapping the
data source requires no business-logic changes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.core.config import Settings
from app.seed.channels import SEED_CHANNELS

logger = logging.getLogger("wavepalace.repository")


class ChannelRepository(ABC):
    @abstractmethod
    async def list_channels(self) -> list[dict]:
        """Return all channels (published and unpublished). Filtering is the
        responsibility of the service layer."""

    @abstractmethod
    async def get_by_slug(self, slug: str) -> dict | None:
        """Return a single channel by slug, or None if not found."""


class SeedChannelRepository(ChannelRepository):
    """In-memory repository backed by static seed data."""

    def __init__(self, channels: list[dict] | None = None) -> None:
        self._channels = channels if channels is not None else SEED_CHANNELS

    async def list_channels(self) -> list[dict]:
        return list(self._channels)

    async def get_by_slug(self, slug: str) -> dict | None:
        return next((c for c in self._channels if c["slug"] == slug), None)


class MongoChannelRepository(ChannelRepository):
    """MongoDB-backed repository using PyMongo Async.

    Kept import-light: the driver is only imported when this class is used,
    so seed mode never requires pymongo to be installed.
    """

    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient  # type: ignore

        self._client = AsyncMongoClient(uri)
        self._collection = self._client[database]["channels"]

    async def list_channels(self) -> list[dict]:
        cursor = self._collection.find({}, {"_id": 0})
        return [doc async for doc in cursor]

    async def get_by_slug(self, slug: str) -> dict | None:
        return await self._collection.find_one({"slug": slug}, {"_id": 0})


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
