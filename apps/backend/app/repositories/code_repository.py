"""Repository layer for Slice 9 channel codes."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from app.schemas.code import CodeDocument

logger = logging.getLogger("wavepalace.codes")


class CodeRepository(ABC):
    @abstractmethod
    async def create(self, doc: CodeDocument) -> CodeDocument: ...

    @abstractmethod
    async def get(self, code: str) -> CodeDocument | None: ...

    @abstractmethod
    async def list_all(self) -> list[CodeDocument]: ...

    @abstractmethod
    async def deactivate(self, code: str) -> bool: ...

    @abstractmethod
    async def code_exists_active(self, code: str) -> bool: ...


class SeedCodeRepository(CodeRepository):
    def __init__(self) -> None:
        self._codes: list[CodeDocument] = []

    async def create(self, doc: CodeDocument) -> CodeDocument:
        self._codes.append(doc)
        return doc

    async def get(self, code: str) -> CodeDocument | None:
        return next((c for c in self._codes if c.code == code), None)

    async def list_all(self) -> list[CodeDocument]:
        return sorted(self._codes, key=lambda c: c.created_at, reverse=True)

    async def deactivate(self, code: str) -> bool:
        for i, c in enumerate(self._codes):
            if c.code == code:
                self._codes[i] = c.model_copy(update={"active": False})
                return True
        return False

    async def code_exists_active(self, code: str) -> bool:
        return any(c.code == code and c.active for c in self._codes)


class MongoCodeRepository(CodeRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        self._col = AsyncMongoClient(uri)[database]["codes"]

    async def create(self, doc: CodeDocument) -> CodeDocument:
        await self._col.insert_one({**doc.model_dump(), "_id": doc.code})
        return doc

    async def get(self, code: str) -> CodeDocument | None:
        doc = await self._col.find_one({"code": code}, {"_id": 0})
        return CodeDocument(**doc) if doc else None

    async def list_all(self) -> list[CodeDocument]:
        cursor = self._col.find({}, {"_id": 0}).sort("created_at", -1)
        return [CodeDocument(**d) async for d in cursor]

    async def deactivate(self, code: str) -> bool:
        result = await self._col.update_one({"code": code}, {"$set": {"active": False}})
        return result.matched_count > 0

    async def code_exists_active(self, code: str) -> bool:
        doc = await self._col.find_one({"code": code, "active": True})
        return doc is not None


def build_code_repository(settings) -> CodeRepository:
    if settings.use_seed_mode:
        return SeedCodeRepository()
    try:
        return MongoCodeRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo code repo failed — falling back to seed mode.")
        return SeedCodeRepository()
