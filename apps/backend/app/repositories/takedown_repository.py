"""Repository layer for DMCA takedown requests."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.schemas.takedown import TakedownDocument

logger = logging.getLogger("wavepalace.takedowns")


class TakedownRepository(ABC):
    @abstractmethod
    async def create(self, doc: TakedownDocument) -> TakedownDocument: ...

    @abstractmethod
    async def get(self, takedown_id: str) -> TakedownDocument | None: ...

    @abstractmethod
    async def list_all(self) -> list[TakedownDocument]: ...

    @abstractmethod
    async def update_status(
        self, takedown_id: str, status: str, notes: str | None
    ) -> TakedownDocument | None: ...


class SeedTakedownRepository(TakedownRepository):
    def __init__(self) -> None:
        self._records: list[TakedownDocument] = []

    async def create(self, doc: TakedownDocument) -> TakedownDocument:
        self._records.append(doc)
        return doc

    async def get(self, takedown_id: str) -> TakedownDocument | None:
        return next((r for r in self._records if r.id == takedown_id), None)

    async def list_all(self) -> list[TakedownDocument]:
        return sorted(self._records, key=lambda r: r.submitted_at, reverse=True)

    async def update_status(
        self, takedown_id: str, status: str, notes: str | None
    ) -> TakedownDocument | None:
        for i, r in enumerate(self._records):
            if r.id == takedown_id:
                updated = r.model_copy(update={"status": status, "notes": notes})
                self._records[i] = updated
                return updated
        return None


class MongoTakedownRepository(TakedownRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["takedowns"]

    async def create(self, doc: TakedownDocument) -> TakedownDocument:
        await self._col.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get(self, takedown_id: str) -> TakedownDocument | None:
        doc = await self._col.find_one({"id": takedown_id}, {"_id": 0})
        return TakedownDocument(**doc) if doc else None

    async def list_all(self) -> list[TakedownDocument]:
        cursor = self._col.find({}, {"_id": 0}).sort("submitted_at", -1)
        return [TakedownDocument(**d) async for d in cursor]

    async def update_status(
        self, takedown_id: str, status: str, notes: str | None
    ) -> TakedownDocument | None:
        result = await self._col.find_one_and_update(
            {"id": takedown_id},
            {"$set": {"status": status, "notes": notes}},
            return_document=True,
            projection={"_id": 0},
        )
        return TakedownDocument(**result) if result else None


def build_takedown_repository(settings) -> TakedownRepository:
    if settings.use_seed_mode:
        return SeedTakedownRepository()
    try:
        return MongoTakedownRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo takedown repo failed — falling back to seed mode.")
        return SeedTakedownRepository()
