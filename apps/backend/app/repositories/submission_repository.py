"""Repository layer for public DJ / artist submissions."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4

from app.core.config import Settings
from app.models.submission import SubmissionDocument
from app.schemas.submission import SubmissionRequest

logger = logging.getLogger("wavepalace.submissions")


class SubmissionRepository(ABC):
    @abstractmethod
    async def create(self, submission: SubmissionRequest) -> SubmissionDocument:
        """Persist a submission and return the stored document."""

    @abstractmethod
    async def list_pending(self) -> list[SubmissionDocument]:
        """Return pending submissions (admin convenience; prefer list_by_status)."""

    @abstractmethod
    async def list_by_status(self, status: str) -> list[SubmissionDocument]:
        """Return submissions filtered by status, newest first."""

    @abstractmethod
    async def get_by_id(self, id: str) -> SubmissionDocument | None:
        """Return one submission by id, or None."""

    @abstractmethod
    async def update_review(
        self, id: str, status: str, reviewer_notes: str | None
    ) -> SubmissionDocument | None:
        """Set status + reviewed_at + reviewer_notes. Returns updated doc or None."""


class SeedSubmissionRepository(SubmissionRepository):
    def __init__(self) -> None:
        self._submissions: list[SubmissionDocument] = []

    async def create(self, submission: SubmissionRequest) -> SubmissionDocument:
        document = SubmissionDocument(
            id=str(uuid4()),
            **submission.model_dump(mode="json"),
            status="pending",
            submitted_at=datetime.utcnow(),
        )
        self._submissions.append(document)
        return document

    async def list_pending(self) -> list[SubmissionDocument]:
        return await self.list_by_status("pending")

    async def list_by_status(self, status: str) -> list[SubmissionDocument]:
        return sorted(
            [s for s in self._submissions if s.status == status],
            key=lambda s: s.submitted_at,
            reverse=True,
        )

    async def get_by_id(self, id: str) -> SubmissionDocument | None:
        return next((s for s in self._submissions if s.id == id), None)

    async def update_review(
        self, id: str, status: str, reviewer_notes: str | None
    ) -> SubmissionDocument | None:
        for i, s in enumerate(self._submissions):
            if s.id == id:
                updated = s.model_copy(
                    update={
                        "status": status,
                        "reviewed_at": datetime.utcnow(),
                        "reviewer_notes": reviewer_notes,
                    }
                )
                self._submissions[i] = updated
                return updated
        return None


class MongoSubmissionRepository(SubmissionRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient  # type: ignore

        self._client = AsyncMongoClient(uri)
        self._collection = self._client[database]["submissions"]

    async def create(self, submission: SubmissionRequest) -> SubmissionDocument:
        document = SubmissionDocument(
            id=str(uuid4()),
            **submission.model_dump(mode="json"),
            status="pending",
            submitted_at=datetime.utcnow(),
        )
        await self._collection.insert_one(document.model_dump(mode="json"))
        return document

    async def list_pending(self) -> list[SubmissionDocument]:
        return await self.list_by_status("pending")

    async def list_by_status(self, status: str) -> list[SubmissionDocument]:
        cursor = self._collection.find({"status": status}, {"_id": 0}).sort("submitted_at", -1)
        return [SubmissionDocument.model_validate(doc) async for doc in cursor]

    async def get_by_id(self, id: str) -> SubmissionDocument | None:
        doc = await self._collection.find_one({"id": id}, {"_id": 0})
        return SubmissionDocument.model_validate(doc) if doc else None

    async def update_review(
        self, id: str, status: str, reviewer_notes: str | None
    ) -> SubmissionDocument | None:
        doc = await self._collection.find_one_and_update(
            {"id": id},
            {"$set": {
                "status": status,
                "reviewed_at": datetime.utcnow(),
                "reviewer_notes": reviewer_notes,
            }},
            return_document=True,
            projection={"_id": 0},
        )
        return SubmissionDocument.model_validate(doc) if doc else None


def build_submission_repository(settings: Settings) -> SubmissionRepository:
    if settings.use_seed_mode:
        return SeedSubmissionRepository()

    try:
        return MongoSubmissionRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:  # pragma: no cover - defensive fallback
        logger.exception("Mongo submissions connection failed; using in-memory submissions.")
        return SeedSubmissionRepository()
