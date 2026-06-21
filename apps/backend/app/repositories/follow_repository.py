"""Repository layer for Slice 9 follows."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.schemas.follow import FollowDocument

logger = logging.getLogger("wavepalace.follows")


class FollowRepository(ABC):
    @abstractmethod
    async def create(self, doc: FollowDocument) -> FollowDocument: ...

    @abstractmethod
    async def get(self, follow_id: str) -> FollowDocument | None: ...

    @abstractmethod
    async def get_by_identity(
        self, discord_user_id: str | None, email: str | None
    ) -> list[FollowDocument]: ...

    @abstractmethod
    async def get_by_channel(self, channel_slug: str) -> list[FollowDocument]: ...

    @abstractmethod
    async def update(self, follow_id: str, updates: dict) -> FollowDocument | None: ...

    @abstractmethod
    async def delete(self, follow_id: str) -> bool: ...

    @abstractmethod
    async def exists(
        self,
        entity_id: str,
        notification_channel: str,
        discord_user_id: str | None,
        email: str | None,
    ) -> bool: ...

    @abstractmethod
    async def get_all_follows(self) -> list[FollowDocument]: ...


class SeedFollowRepository(FollowRepository):
    def __init__(self) -> None:
        self._follows: list[FollowDocument] = []

    async def create(self, doc: FollowDocument) -> FollowDocument:
        self._follows.append(doc)
        return doc

    async def get(self, follow_id: str) -> FollowDocument | None:
        return next((f for f in self._follows if f.id == follow_id), None)

    async def get_by_identity(
        self, discord_user_id: str | None, email: str | None
    ) -> list[FollowDocument]:
        result = []
        for f in self._follows:
            if discord_user_id and f.discord_user_id == discord_user_id:
                result.append(f)
            elif email and f.email == email:
                result.append(f)
        return result

    async def get_by_channel(self, channel_slug: str) -> list[FollowDocument]:
        return [f for f in self._follows if f.channel_slug == channel_slug and f.confirmed]

    async def update(self, follow_id: str, updates: dict) -> FollowDocument | None:
        for i, f in enumerate(self._follows):
            if f.id == follow_id:
                self._follows[i] = f.model_copy(update=updates)
                return self._follows[i]
        return None

    async def delete(self, follow_id: str) -> bool:
        for i, f in enumerate(self._follows):
            if f.id == follow_id:
                self._follows.pop(i)
                return True
        return False

    async def exists(
        self,
        entity_id: str,
        notification_channel: str,
        discord_user_id: str | None,
        email: str | None,
    ) -> bool:
        for f in self._follows:
            if f.entity_id != entity_id or f.notification_channel != notification_channel:
                continue
            if discord_user_id and f.discord_user_id == discord_user_id:
                return True
            if email and f.email == email:
                return True
        return False

    async def get_all_follows(self) -> list[FollowDocument]:
        return [f for f in self._follows if f.confirmed]


class MongoFollowRepository(FollowRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["follows"]

    async def create(self, doc: FollowDocument) -> FollowDocument:
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get(self, follow_id: str) -> FollowDocument | None:
        doc = await self._col.find_one({"id": follow_id}, {"_id": 0})
        return FollowDocument(**doc) if doc else None

    async def get_by_identity(
        self, discord_user_id: str | None, email: str | None
    ) -> list[FollowDocument]:
        conditions = []
        if discord_user_id:
            conditions.append({"discord_user_id": discord_user_id})
        if email:
            conditions.append({"email": email})
        if not conditions:
            return []
        cursor = self._col.find({"$or": conditions}, {"_id": 0})
        return [FollowDocument(**d) async for d in cursor]

    async def get_by_channel(self, channel_slug: str) -> list[FollowDocument]:
        cursor = self._col.find(
            {"channel_slug": channel_slug, "confirmed": True}, {"_id": 0}
        )
        return [FollowDocument(**d) async for d in cursor]

    async def update(self, follow_id: str, updates: dict) -> FollowDocument | None:
        result = await self._col.find_one_and_update(
            {"id": follow_id},
            {"$set": updates},
            return_document=True,
            projection={"_id": 0},
        )
        return FollowDocument(**result) if result else None

    async def delete(self, follow_id: str) -> bool:
        result = await self._col.delete_one({"id": follow_id})
        return result.deleted_count > 0

    async def exists(
        self,
        entity_id: str,
        notification_channel: str,
        discord_user_id: str | None,
        email: str | None,
    ) -> bool:
        query: dict = {"entity_id": entity_id, "notification_channel": notification_channel}
        if discord_user_id:
            query["discord_user_id"] = discord_user_id
        elif email:
            query["email"] = email
        return await self._col.find_one(query) is not None

    async def get_all_follows(self) -> list[FollowDocument]:
        cursor = self._col.find({"confirmed": True}, {"_id": 0})
        return [FollowDocument(**d) async for d in cursor]


def build_follow_repository(settings) -> FollowRepository:
    if settings.use_seed_mode:
        return SeedFollowRepository()
    try:
        return MongoFollowRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo follow repo failed — falling back to seed mode.")
        return SeedFollowRepository()
