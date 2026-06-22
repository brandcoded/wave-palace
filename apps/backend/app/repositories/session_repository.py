"""Repository layer for sessions and email login tokens (Slice 10)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.user import EmailLoginTokenDocument, SessionDocument

logger = logging.getLogger("wavepalace.sessions")


class SessionRepository(ABC):
    @abstractmethod
    async def create(self, doc: SessionDocument) -> SessionDocument: ...

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionDocument]: ...

    @abstractmethod
    async def revoke(self, session_id: str) -> None: ...

    @abstractmethod
    async def create_email_token(self, doc: EmailLoginTokenDocument) -> EmailLoginTokenDocument: ...

    @abstractmethod
    async def get_email_token_by_hash(self, token_hash: str) -> Optional[EmailLoginTokenDocument]: ...

    @abstractmethod
    async def consume_email_token(self, token_id: str) -> None: ...


class SeedSessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, SessionDocument] = {}
        self._email_tokens: dict[str, EmailLoginTokenDocument] = {}

    async def create(self, doc: SessionDocument) -> SessionDocument:
        self._sessions[doc.id] = doc
        return doc

    async def get(self, session_id: str) -> Optional[SessionDocument]:
        return self._sessions.get(session_id)

    async def revoke(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id] = self._sessions[session_id].model_copy(
                update={"revoked": True}
            )

    async def create_email_token(self, doc: EmailLoginTokenDocument) -> EmailLoginTokenDocument:
        self._email_tokens[doc.id] = doc
        return doc

    async def get_email_token_by_hash(self, token_hash: str) -> Optional[EmailLoginTokenDocument]:
        return next(
            (t for t in self._email_tokens.values() if t.token_hash == token_hash), None
        )

    async def consume_email_token(self, token_id: str) -> None:
        if token_id in self._email_tokens:
            self._email_tokens[token_id] = self._email_tokens[token_id].model_copy(
                update={"consumed": True}
            )


class MongoSessionRepository(SessionRepository):
    def __init__(self, uri: str, database: str) -> None:
        from pymongo import AsyncMongoClient
        client = AsyncMongoClient(uri)[database]
        self._sessions = client["sessions"]
        self._email_tokens = client["email_login_tokens"]

    async def create(self, doc: SessionDocument) -> SessionDocument:
        await self._sessions.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get(self, session_id: str) -> Optional[SessionDocument]:
        doc = await self._sessions.find_one({"id": session_id}, {"_id": 0})
        return SessionDocument(**doc) if doc else None

    async def revoke(self, session_id: str) -> None:
        await self._sessions.update_one({"id": session_id}, {"$set": {"revoked": True}})

    async def create_email_token(self, doc: EmailLoginTokenDocument) -> EmailLoginTokenDocument:
        await self._email_tokens.insert_one({**doc.model_dump(), "_id": doc.id})
        return doc

    async def get_email_token_by_hash(self, token_hash: str) -> Optional[EmailLoginTokenDocument]:
        doc = await self._email_tokens.find_one({"token_hash": token_hash}, {"_id": 0})
        return EmailLoginTokenDocument(**doc) if doc else None

    async def consume_email_token(self, token_id: str) -> None:
        await self._email_tokens.update_one(
            {"id": token_id}, {"$set": {"consumed": True}}
        )


def build_session_repository(settings) -> SessionRepository:
    if settings.use_seed_mode:
        return SeedSessionRepository()
    try:
        return MongoSessionRepository(settings.mongodb_uri, settings.mongodb_database)
    except Exception:
        logger.exception("Mongo session repo failed — falling back to seed mode.")
        return SeedSessionRepository()
