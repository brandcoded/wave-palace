"""Repository layer for Slice 12 — notification inbox."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.me import NotificationCreate, NotificationDocument

logger = logging.getLogger("wavepalace.notifications")


class NotificationRepository(ABC):
    @abstractmethod
    async def create(self, notif: NotificationCreate) -> NotificationDocument: ...

    @abstractmethod
    async def get_by_user(self, user_id: str, limit: int = 50) -> list[NotificationDocument]: ...

    @abstractmethod
    async def mark_read(self, notif_id: str, user_id: str) -> bool: ...

    @abstractmethod
    async def mark_all_read(self, user_id: str) -> int: ...

    @abstractmethod
    async def unread_count(self, user_id: str) -> int: ...


class SeedNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self._notifs: list[NotificationDocument] = []

    async def create(self, notif: NotificationCreate) -> NotificationDocument:
        doc = NotificationDocument(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            **notif.model_dump(),
        )
        self._notifs.append(doc)
        return doc

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[NotificationDocument]:
        result = [n for n in self._notifs if n.user_id == user_id]
        result.sort(key=lambda n: (n.read, -n.created_at.timestamp()))
        return result[:limit]

    async def mark_read(self, notif_id: str, user_id: str) -> bool:
        for i, n in enumerate(self._notifs):
            if n.id == notif_id and n.user_id == user_id:
                self._notifs[i] = n.model_copy(update={"read": True})
                return True
        return False

    async def mark_all_read(self, user_id: str) -> int:
        count = 0
        for i, n in enumerate(self._notifs):
            if n.user_id == user_id and not n.read:
                self._notifs[i] = n.model_copy(update={"read": True})
                count += 1
        return count

    async def unread_count(self, user_id: str) -> int:
        return sum(1 for n in self._notifs if n.user_id == user_id and not n.read)


class MongoNotificationRepository(NotificationRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["notifications"]

    async def create(self, notif: NotificationCreate) -> NotificationDocument:
        doc = NotificationDocument(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            **notif.model_dump(),
        )
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[NotificationDocument]:
        cursor = self._col.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort([("read", 1), ("created_at", -1)]).limit(limit)
        return [NotificationDocument(**d) async for d in cursor]

    async def mark_read(self, notif_id: str, user_id: str) -> bool:
        result = await self._col.update_one(
            {"id": notif_id, "user_id": user_id},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0

    async def mark_all_read(self, user_id: str) -> int:
        result = await self._col.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count

    async def unread_count(self, user_id: str) -> int:
        return await self._col.count_documents({"user_id": user_id, "read": False})


def build_notification_repository(settings) -> NotificationRepository:
    if settings.use_seed_mode:
        return SeedNotificationRepository()
    try:
        return MongoNotificationRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo notification repo failed — falling back to seed mode.")
        return SeedNotificationRepository()
