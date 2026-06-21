"""Analytics aggregation service for Slice 7 — read-only, no new event collection."""

from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.channel_repository import ChannelRepository
from app.repositories.code_repository import CodeRepository
from app.repositories.follow_repository import FollowRepository
from app.schemas.analytics import AnalyticsSummaryResponse, ChannelStatResponse


class AnalyticsService:
    def __init__(
        self,
        channel_repo: ChannelRepository,
        follow_repo: FollowRepository,
        code_repo: CodeRepository,
    ) -> None:
        self._channels = channel_repo
        self._follows = follow_repo
        self._codes = code_repo

    async def get_summary(self) -> AnalyticsSummaryResponse:
        channels = await self._channels.list_channels()
        all_follows = await self._follows.get_all_follows()
        all_codes = await self._codes.list_all()

        # Index follows and active code counts by channel slug
        follows_by_channel: dict[str, list] = {}
        for f in all_follows:
            follows_by_channel.setdefault(f.channel_slug, []).append(f)

        active_codes_by_channel: dict[str, int] = {}
        for c in all_codes:
            if c.active:
                active_codes_by_channel[c.channel_slug] = (
                    active_codes_by_channel.get(c.channel_slug, 0) + 1
                )

        channel_stats: list[ChannelStatResponse] = []
        total_plays = 0
        total_follows = 0
        published_count = 0
        channels_with_sponsor = 0
        global_breakdown: dict[str, int] = {"discord": 0, "email": 0, "browser_push": 0}

        for ch in channels:
            slug = ch["slug"]
            play_count = ch.get("playCount", 0)
            is_published = ch.get("isPublished", True)
            streaming_active = ch.get("streamingActive", False)
            sponsor = ch.get("sponsor")
            sponsor_active = bool(sponsor and sponsor.get("isActive"))
            mux_last_at = ch.get("muxLastAt")

            ch_follows = follows_by_channel.get(slug, [])
            breakdown: dict[str, int] = {"discord": 0, "email": 0, "browser_push": 0}
            for f in ch_follows:
                nc = f.notification_channel
                breakdown[nc] = breakdown.get(nc, 0) + 1

            total_plays += play_count
            total_follows += len(ch_follows)
            if is_published:
                published_count += 1
            if sponsor_active:
                channels_with_sponsor += 1
            for k, v in breakdown.items():
                global_breakdown[k] = global_breakdown.get(k, 0) + v

            channel_stats.append(
                ChannelStatResponse(
                    slug=slug,
                    title=ch.get("title", slug),
                    host_name=ch.get("hostName", ""),
                    play_count=play_count,
                    follow_count=len(ch_follows),
                    follow_breakdown=breakdown,
                    active_code_count=active_codes_by_channel.get(slug, 0),
                    is_published=is_published,
                    streaming_active=streaming_active,
                    mux_last_at=mux_last_at,
                )
            )

        channel_stats.sort(key=lambda s: s.play_count, reverse=True)

        return AnalyticsSummaryResponse(
            total_plays=total_plays,
            total_follows=total_follows,
            total_channels=len(channels),
            published_channels=published_count,
            channels_with_sponsor=channels_with_sponsor,
            follow_breakdown=global_breakdown,
            top_channels=channel_stats,
            generated_at=datetime.now(timezone.utc),
        )
