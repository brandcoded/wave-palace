"""Repository layer for User documents (Slice 10)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from app.schemas.user import BOOTSTRAP_ADMIN_ID, UserDocument

logger = logging.getLogger("wavepalace.users")

_SEED_ADMIN = UserDocument(
    id=BOOTSTRAP_ADMIN_ID,
    email="admin@wavepalace.local",
    display_name="Admin",
    roles=["admin"],
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    is_active=True,
)


class UserRepository(ABC):
    @abstractmethod
    async def create(self, doc: UserDocument) -> UserDocument: ...

    @abstractmethod
    async def get(self, user_id: str) -> Optional[UserDocument]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserDocument]: ...

    @abstractmethod
    async def get_by_discord_id(self, discord_user_id: str) -> Optional[UserDocument]: ...

    @abstractmethod
    async def update(self, user_id: str, updates: dict) -> Optional[UserDocument]: ...

    @abstractmethod
    async def list_all(self) -> list[UserDocument]: ...

    @abstractmethod
    async def upsert(self, doc: UserDocument) -> UserDocument: ...


class SeedUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: list[UserDocument] = [_SEED_ADMIN]

    async def create(self, doc: UserDocument) -> UserDocument:
        self._users.append(doc)
        return doc

    async def get(self, user_id: str) -> Optional[UserDocument]:
        return next((u for u in self._users if u.id == user_id), None)

    async def get_by_email(self, email: str) -> Optional[UserDocument]:
        return next((u for u in self._users if u.email == email), None)

    async def get_by_discord_id(self, discord_user_id: str) -> Optional[UserDocument]:
        return next((u for u in self._users if u.discord_user_id == discord_user_id), None)

    async def update(self, user_id: str, updates: dict) -> Optional[UserDocument]:
        for i, u in enumerate(self._users):
            if u.id == user_id:
                self._users[i] = u.model_copy(update=updates)
                return self._users[i]
        return None

    async def list_all(self) -> list[UserDocument]:
        return list(self._users)

    async def upsert(self, doc: UserDocument) -> UserDocument:
        for i, u in enumerate(self._users):
            if u.id == doc.id:
                self._users[i] = doc
                return doc
        self._users.append(doc)
        return doc


class MongoUserRepository(UserRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["users"]

    async def create(self, doc: UserDocument) -> UserDocument:
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get(self, user_id: str) -> Optional[UserDocument]:
        doc = await self._col.find_one({"id": user_id}, {"_id": 0})
        return UserDocument(**doc) if doc else None

    async def get_by_email(self, email: str) -> Optional[UserDocument]:
        doc = await self._col.find_one({"email": email}, {"_id": 0})
        return UserDocument(**doc) if doc else None

    async def get_by_discord_id(self, discord_user_id: str) -> Optional[UserDocument]:
        doc = await self._col.find_one({"discord_user_id": discord_user_id}, {"_id": 0})
        return UserDocument(**doc) if doc else None

    async def update(self, user_id: str, updates: dict) -> Optional[UserDocument]:
        result = await self._col.find_one_and_update(
            {"id": user_id},
            {"$set": updates},
            return_document=True,
            projection={"_id": 0},
        )
        return UserDocument(**result) if result else None

    async def list_all(self) -> list[UserDocument]:
        cursor = self._col.find({}, {"_id": 0}).sort("created_at", 1)
        return [UserDocument(**d) async for d in cursor]

    async def upsert(self, doc: UserDocument) -> UserDocument:
        await self._col.update_one(
            {"id": doc.id},
            {"$set": {**doc.model_dump(), "_id": doc.id}},
            upsert=True,
        )
        return doc


def build_user_repository(settings) -> UserRepository:
    if settings.use_seed_mode:
        return SeedUserRepository()
    try:
        return MongoUserRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo user repo failed — falling back to seed mode.")
        return SeedUserRepository()
