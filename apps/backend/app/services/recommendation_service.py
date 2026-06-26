"""Service layer for Slice 12 — tag-based channel recommendations."""

from __future__ import annotations

from typing import Optional

from app.repositories.channel_repository import ChannelRepository
from app.repositories.follow_repository import FollowRepository
from app.schemas.user import UserDocument


class RecommendationService:
    def __init__(self, channel_repo: ChannelRepository, follow_repo: FollowRepository) -> None:
        self._channels = channel_repo
        self._follows = follow_repo

    async def get_recommendations(self, user: UserDocument, limit: int = 6) -> list[dict]:
        follows = await self._follows.get_by_identity(
            discord_user_id=user.discord_user_id,
            email=user.email,
        )
        followed_slugs = {f.channel_slug for f in follows if f.confirmed}

        all_channels = await self._channels.list_channels()
        published = [c for c in all_channels if c.get("isPublished") and c["slug"] not in followed_slugs]

        if followed_slugs:
            followed_chans = [c for c in all_channels if c["slug"] in followed_slugs]
            tags: set[tuple[str, str]] = set()
            for fc in followed_chans:
                for g in (fc.get("genre") or []):
                    tags.add(("genre", g))
                for m in (fc.get("mood") or []):
                    tags.add(("mood", m))

            if tags:
                def _score(ch: dict) -> int:
                    ch_genres = set(ch.get("genre") or [])
                    ch_moods = set(ch.get("mood") or [])
                    return sum(
                        1 for k, v in tags
                        if (k == "genre" and v in ch_genres) or (k == "mood" and v in ch_moods)
                    )

                matched = [(c, _score(c)) for c in published if _score(c) > 0]
                if matched:
                    matched.sort(key=lambda x: (-x[1], -(x[0].get("playCount") or 0)))
                    result = []
                    for ch, _ in matched[:limit]:
                        reason = _find_reason(ch, followed_chans, tags)
                        result.append({**ch, "_reason": reason})
                    return result

        # Fallback: top by play_count
        published.sort(key=lambda c: -(c.get("playCount") or 0))
        return [{**c, "_reason": None} for c in published[:limit]]


def _find_reason(ch: dict, followed_chans: list[dict], tags: set) -> Optional[str]:
    ch_genres = set(ch.get("genre") or [])
    ch_moods = set(ch.get("mood") or [])
    for fc in followed_chans:
        fc_genres = set(fc.get("genre") or [])
        fc_moods = set(fc.get("mood") or [])
        if (fc_genres & ch_genres) or (fc_moods & ch_moods):
            return f"Because you follow {fc.get('title', fc['slug'])}"
    return None
