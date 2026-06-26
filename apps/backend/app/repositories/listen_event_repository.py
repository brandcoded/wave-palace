"""Repository layer for Slice 12 — listen history."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timezone

from app.schemas.me import ListenEventCreate, ListenEventDocument

logger = logging.getLogger("wavepalace.listen_events")


class ListenEventRepository(ABC):
    @abstractmethod
    async def record(self, event: ListenEventCreate) -> ListenEventDocument: ...

    @abstractmethod
    async def get_by_user(self, user_id: str, limit: int = 50) -> list[ListenEventDocument]: ...

    @abstractmethod
    async def merge_session(self, session_key: str, user_id: str) -> int: ...

    @abstractmethod
    async def get_top_channel(self, user_id: str, since: datetime) -> str | None: ...

    @abstractmethod
    async def get_last_channel(self, user_id: str) -> str | None: ...


class SeedListenEventRepository(ListenEventRepository):
    def __init__(self) -> None:
        self._events: list[ListenEventDocument] = []

    async def record(self, event: ListenEventCreate) -> ListenEventDocument:
        doc = ListenEventDocument(
            id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            **event.model_dump(),
        )
        self._events.append(doc)
        return doc

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[ListenEventDocument]:
        result = [e for e in self._events if e.user_id == user_id]
        result.sort(key=lambda e: e.started_at, reverse=True)
        return result[:limit]

    async def merge_session(self, session_key: str, user_id: str) -> int:
        count = 0
        for i, e in enumerate(self._events):
            if e.session_key == session_key and e.user_id is None:
                self._events[i] = e.model_copy(update={"user_id": user_id})
                count += 1
        return count

    async def get_top_channel(self, user_id: str, since: datetime) -> str | None:
        events = [e for e in self._events if e.user_id == user_id and e.started_at >= since]
        if not events:
            return None
        counts = Counter(e.channel_slug for e in events)
        return counts.most_common(1)[0][0]

    async def get_last_channel(self, user_id: str) -> str | None:
        events = [e for e in self._events if e.user_id == user_id]
        if not events:
            return None
        return max(events, key=lambda e: e.started_at).channel_slug


class MongoListenEventRepository(ListenEventRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["listen_events"]

    async def record(self, event: ListenEventCreate) -> ListenEventDocument:
        doc = ListenEventDocument(
            id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            **event.model_dump(),
        )
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[ListenEventDocument]:
        cursor = self._col.find({"user_id": user_id}, {"_id": 0}).sort("started_at", -1).limit(limit)
        return [ListenEventDocument(**d) async for d in cursor]

    async def merge_session(self, session_key: str, user_id: str) -> int:
        result = await self._col.update_many(
            {"session_key": session_key, "user_id": None},
            {"$set": {"user_id": user_id}},
        )
        return result.modified_count

    async def get_top_channel(self, user_id: str, since: datetime) -> str | None:
        pipeline = [
            {"$match": {"user_id": user_id, "started_at": {"$gte": since}}},
            {"$group": {"_id": "$channel_slug", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 1},
        ]
        async for doc in self._col.aggregate(pipeline):
            return doc["_id"]
        return None

    async def get_last_channel(self, user_id: str) -> str | None:
        doc = await self._col.find_one(
            {"user_id": user_id}, {"channel_slug": 1, "_id": 0},
            sort=[("started_at", -1)],
        )
        return doc["channel_slug"] if doc else None


def build_listen_event_repository(settings) -> ListenEventRepository:
    if settings.use_seed_mode:
        return SeedListenEventRepository()
    try:
        return MongoListenEventRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo listen-event repo failed — falling back to seed mode.")
        return SeedListenEventRepository()
