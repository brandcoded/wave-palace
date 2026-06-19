"""Repository layer for admin-managed submission option lists."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from app.core.config import Settings
from app.seed.submission_options import SEED_SUBMISSION_OPTIONS

logger = logging.getLogger("wavepalace.submission_options")

OPTION_FIELDS = ("genre", "mood", "energy", "theme")


class SubmissionOptionsRepository(ABC):
    @abstractmethod
    async def get_all(self) -> dict[str, list[str]]:
        """Return all submission option lists keyed by field name."""

    @abstractmethod
    async def upsert(self, field: str, options: list[str]) -> None:
        """Create or replace one option list."""


class SeedSubmissionOptionsRepository(SubmissionOptionsRepository):
    def __init__(self, options: dict[str, list[str]] | None = None) -> None:
        self._options = {
            key: list(value)
            for key, value in (options or SEED_SUBMISSION_OPTIONS).items()
        }

    async def get_all(self) -> dict[str, list[str]]:
        return {field: list(self._options[field]) for field in OPTION_FIELDS}

    async def upsert(self, field: str, options: list[str]) -> None:
        if field not in OPTION_FIELDS:
            raise ValueError(f"Unknown submission option field: {field}")
        self._options[field] = list(options)


class MongoSubmissionOptionsRepository(SubmissionOptionsRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient  # type: ignore

        self._client = AsyncMongoClient(uri)
        self._collection = self._client[database]["submission_options"]

    async def get_all(self) -> dict[str, list[str]]:
        docs = [doc async for doc in self._collection.find({}, {"_id": 0})]
        if not docs:
            for field, options in SEED_SUBMISSION_OPTIONS.items():
                await self.upsert(field, options)
            return {field: list(options) for field, options in SEED_SUBMISSION_OPTIONS.items()}

        by_field = {doc["field"]: list(doc.get("options", [])) for doc in docs}
        return {
            field: list(by_field.get(field) or SEED_SUBMISSION_OPTIONS[field])
            for field in OPTION_FIELDS
        }

    async def upsert(self, field: str, options: list[str]) -> None:
        if field not in OPTION_FIELDS:
            raise ValueError(f"Unknown submission option field: {field}")
        await self._collection.update_one(
            {"field": field},
            {"$set": {"field": field, "options": list(options), "updated_at": datetime.utcnow()}},
            upsert=True,
        )


def build_submission_options_repository(settings: Settings) -> SubmissionOptionsRepository:
    if settings.use_seed_mode:
        return SeedSubmissionOptionsRepository()

    try:
        return MongoSubmissionOptionsRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:  # pragma: no cover - defensive fallback
        logger.exception("Mongo submission options connection failed; using seed options.")
        return SeedSubmissionOptionsRepository()
