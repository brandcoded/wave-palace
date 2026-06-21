"""Pydantic response schemas for the Production Analytics Dashboard (Slice 7)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChannelStatResponse(BaseModel):
    slug: str
    title: str
    host_name: str
    play_count: int
    follow_count: int
    follow_breakdown: dict[str, int]
    active_code_count: int
    is_published: bool
    streaming_active: bool
    mux_last_at: Optional[datetime] = None


class AnalyticsSummaryResponse(BaseModel):
    total_plays: int
    total_follows: int
    total_channels: int
    published_channels: int
    channels_with_sponsor: int
    follow_breakdown: dict[str, int]
    top_channels: list[ChannelStatResponse]
    generated_at: datetime
