"""Pydantic schemas for the Channel domain (data/transport contract)."""

from datetime import datetime

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
    genre: str
    mood: str
    energy: str
    theme: str
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

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: str
    service: str
