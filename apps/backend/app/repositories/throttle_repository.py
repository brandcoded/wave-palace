"""Throttle repository for Slice 13 — prevents notification spam.

ThrottleRecord.user_id stores either a real UserDocument.id or a synthetic
"follow:{follow_id}" key when no user account exists for a follow.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

logger = logging.getLogger("wavepalace.throttle")


class ThrottleRecord(BaseModel):
    user_id: str
    channel_slug: str
    notification_type: str
    last_sent_at: datetime


class ThrottleRepository(ABC):
    @abstractmethod
    async def is_throttled(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
        window_hours: float,
    ) -> bool: ...

    @abstractmethod
    async def record_sent(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
    ) -> None: ...


class SeedThrottleRepository(ThrottleRepository):
    def __init__(self) -> None:
        # keyed by (user_id, channel_slug, notification_type)
        self._records: dict[tuple[str, str, str], datetime] = {}

    async def is_throttled(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
        window_hours: float,
    ) -> bool:
        key = (user_id, channel_slug, notification_type)
        last = self._records.get(key)
        if last is None:
            return False
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
        return last > cutoff

    async def record_sent(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
    ) -> None:
        self._records[(user_id, channel_slug, notification_type)] = datetime.now(tz=timezone.utc)


class MongoThrottleRepository(ThrottleRepository):
    def __init__(self, uri: str, database: str) -> None:
        import motor.motor_asyncio as motor
        client: motor.AsyncIOMotorClient = motor.AsyncIOMotorClient(uri)
        self._col = client[database]["notification_throttle"]

    async def _ensure_ttl_index(self) -> None:
        await self._col.create_index(
            "last_sent_at",
            expireAfterSeconds=604800,  # 7 days
        )

    async def is_throttled(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
        window_hours: float,
    ) -> bool:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
        doc = await self._col.find_one(
            {
                "user_id": user_id,
                "channel_slug": channel_slug,
                "notification_type": notification_type,
                "last_sent_at": {"$gt": cutoff},
            }
        )
        return doc is not None

    async def record_sent(
        self,
        user_id: str,
        channel_slug: str,
        notification_type: str,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        await self._col.update_one(
            {
                "user_id": user_id,
                "channel_slug": channel_slug,
                "notification_type": notification_type,
            },
            {"$set": {"last_sent_at": now}},
            upsert=True,
        )
