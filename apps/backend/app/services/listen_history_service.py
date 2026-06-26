"""Service layer for Slice 12 — listen history."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.repositories.listen_event_repository import ListenEventRepository
from app.schemas.me import ListenEventCreate, ListenEventDocument


class ListenHistoryService:
    def __init__(self, repo: ListenEventRepository) -> None:
        self._repo = repo

    async def record_play(
        self,
        user_id: Optional[str],
        session_key: Optional[str],
        channel_slug: str,
        track_title: Optional[str],
        track_artist: Optional[str],
    ) -> ListenEventDocument:
        return await self._repo.record(ListenEventCreate(
            user_id=user_id,
            session_key=session_key,
            channel_slug=channel_slug,
            track_title=track_title,
            track_artist=track_artist,
        ))

    async def merge_anonymous(self, session_key: str, user_id: str) -> int:
        return await self._repo.merge_session(session_key, user_id)

    async def get_history(self, user_id: str) -> dict:
        recent = await self._repo.get_by_user(user_id, limit=50)
        since = datetime.now(timezone.utc) - timedelta(days=30)
        top_channel = await self._repo.get_top_channel(user_id, since)
        last_channel = await self._repo.get_last_channel(user_id)
        return {
            "recent": [e.model_dump() for e in recent],
            "top_channel": top_channel,
            "last_channel": last_channel,
        }
