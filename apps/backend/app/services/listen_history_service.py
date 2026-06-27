"""Service layer for Slice 12 — listen history."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.repositories.listen_event_repository import ListenEventRepository
from app.schemas.me import ListenEventCreate, ListenEventDocument

logger = logging.getLogger("wavepalace.listen_history")


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
        # Each sub-query is isolated so one failure (e.g. a malformed legacy
        # document or an aggregation hiccup) degrades that field instead of
        # 500-ing the whole dashboard.
        since = datetime.now(timezone.utc) - timedelta(days=30)
        try:
            recent = await self._repo.get_by_user(user_id, limit=50)
        except Exception:
            logger.exception("get_by_user failed for %s", user_id)
            recent = []
        try:
            top_channel = await self._repo.get_top_channel(user_id, since)
        except Exception:
            logger.exception("get_top_channel failed for %s", user_id)
            top_channel = None
        try:
            last_channel = await self._repo.get_last_channel(user_id)
        except Exception:
            logger.exception("get_last_channel failed for %s", user_id)
            last_channel = None
        return {
            "recent": [e.model_dump() for e in recent],
            "top_channel": top_channel,
            "last_channel": last_channel,
        }
