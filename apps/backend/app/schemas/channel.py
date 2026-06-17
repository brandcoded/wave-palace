"""Pydantic schemas for the Channel domain (data/transport contract)."""

from pydantic import BaseModel, Field, HttpUrl


class ExternalLink(BaseModel):
    label: str
    url: HttpUrl


class Channel(BaseModel):
    """A curated visual radio channel.

    audioUrl is the music stream used by the web player.
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
    audioUrl: HttpUrl
    vrchatPlaybackUrl: str
    externalLinks: list[ExternalLink] = Field(default_factory=list)
    rightsStatus: str = "owned_or_cleared"
    isPublished: bool = True

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: str
    service: str
