"""Repository layer for Slice 11 channel invite tokens."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.invite import ChannelInviteToken

logger = logging.getLogger("wavepalace.invites")


class InviteRepository(ABC):
    @abstractmethod
    async def create(self, doc: ChannelInviteToken) -> ChannelInviteToken: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> ChannelInviteToken | None: ...

    @abstractmethod
    async def consume(self, token_hash: str, user_id: str) -> bool: ...

    @abstractmethod
    async def list_by_channel(self, channel_slug: str) -> list[ChannelInviteToken]: ...


class SeedInviteRepository(InviteRepository):
    def __init__(self) -> None:
        self._invites: list[ChannelInviteToken] = []

    async def create(self, doc: ChannelInviteToken) -> ChannelInviteToken:
        self._invites.append(doc)
        return doc

    async def get_by_token_hash(self, token_hash: str) -> ChannelInviteToken | None:
        return next((i for i in self._invites if i.token_hash == token_hash), None)

    async def consume(self, token_hash: str, user_id: str) -> bool:
        for idx, inv in enumerate(self._invites):
            if inv.token_hash == token_hash:
                self._invites[idx] = inv.model_copy(
                    update={
                        "consumed": True,
                        "consumed_by_user_id": user_id,
                        "consumed_at": datetime.now(timezone.utc),
                    }
                )
                return True
        return False

    async def list_by_channel(self, channel_slug: str) -> list[ChannelInviteToken]:
        return [i for i in self._invites if i.channel_slug == channel_slug]


class MongoInviteRepository(InviteRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient

        self._col = AsyncMongoClient(uri)[database]["channel_invites"]

    async def create(self, doc: ChannelInviteToken) -> ChannelInviteToken:
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get_by_token_hash(self, token_hash: str) -> ChannelInviteToken | None:
        doc = await self._col.find_one({"token_hash": token_hash}, {"_id": 0})
        return ChannelInviteToken(**doc) if doc else None

    async def consume(self, token_hash: str, user_id: str) -> bool:
        result = await self._col.update_one(
            {"token_hash": token_hash},
            {
                "$set": {
                    "consumed": True,
                    "consumed_by_user_id": user_id,
                    "consumed_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.matched_count > 0

    async def list_by_channel(self, channel_slug: str) -> list[ChannelInviteToken]:
        cursor = self._col.find({"channel_slug": channel_slug}, {"_id": 0}).sort(
            "created_at", -1
        )
        return [ChannelInviteToken(**d) async for d in cursor]


def build_invite_repository(settings) -> InviteRepository:
    if settings.use_seed_mode:
        return SeedInviteRepository()
    try:
        return MongoInviteRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo invite repo failed — falling back to seed mode.")
        return SeedInviteRepository()
