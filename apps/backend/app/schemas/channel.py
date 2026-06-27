"""Pydantic schemas for the Channel domain (data/transport contract)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.sponsor import Sponsor


class ExternalLink(BaseModel):
    label: str
    url: HttpUrl


class TrackItem(BaseModel):
    url: str
    title: str = ""
    artist: str = ""


class Channel(BaseModel):
    """A curated visual radio channel.

    audioUrl is the first track / primary stream used by the web player.
    playlist is the ordered list of tracks (url + title + artist) that cycle automatically.
    coverImageUrl is the static channel art shown as the player background.
    vrchatPlaybackUrl is a pre-muxed static MP4 (image + audio) for VRChat players.
    External streaming links are attribution only and are never playback sources.
    """

    id: str
    slug: str
    title: str
    description: str
    genre: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    energy: list[str] = Field(default_factory=list)
    theme: list[str] = Field(default_factory=list)
    hostName: str = Field(..., alias="hostName")
    coverImageUrl: HttpUrl
    visualLoopUrl: str | None = None  # short looping MP4 used as mux visual; falls back to coverImageUrl
    audioUrl: HttpUrl
    playlist: list[TrackItem] = Field(default_factory=list)
    vrchatPlaybackUrl: str
    externalLinks: list[ExternalLink] = Field(default_factory=list)
    rightsStatus: str = "owned_or_cleared"
    isPublished: bool = True
    playCount: int = 0
    sponsor: Sponsor | None = None
    muxOutdated: bool = False
    muxLastAt: datetime | None = None
    streamingActive: bool = False
    vrchatFallbackUrl: str | None = None
    # Slice 11 — Host Onboarding & Ownership (admin-only; stripped from public API)
    owner_ids: list[str] = Field(default_factory=list)
    auto_publish: bool = True
    # Slice 1C — Audio Visualizer
    visualizer_style: Literal["none", "waveform", "bars", "circular", "blob", "terrain"] = "none"
    visualizer_theme: Literal["violet", "teal", "ember", "rose", "ice", "frequency"] = "violet"
    visualizer_backdrop: Literal["overlay_video", "overlay_image", "replace"] = "overlay_video"
    # Public engagement metrics (populated at read time, not stored)
    follower_count: int = 0
    listener_count: int = 0
    worlds_count: int = 0   # TODO: Slice 4 — populate from VRChat stream session tracking
    trending: bool = False  # TODO: Slice 8 — compute from play_count_7d_ago

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: str
    service: str
