"""Pydantic schemas for Slice 12 — Logged-In Dashboard (me/* endpoints)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ListenEventDocument(BaseModel):
    id: str
    user_id: Optional[str] = None
    session_key: Optional[str] = None
    channel_slug: str
    track_title: Optional[str] = None
    track_artist: Optional[str] = None
    started_at: datetime


class ListenEventCreate(BaseModel):
    user_id: Optional[str] = None
    session_key: Optional[str] = None
    channel_slug: str
    track_title: Optional[str] = None
    track_artist: Optional[str] = None


class ChannelSaveDocument(BaseModel):
    id: str
    user_id: str
    channel_slug: str
    saved_at: datetime


class NotificationDocument(BaseModel):
    id: str
    user_id: str
    type: Literal["new_tracks", "channel_live", "digest", "recommendation"]
    channel_slug: Optional[str] = None
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    read: bool = False
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: str
    type: Literal["new_tracks", "channel_live", "digest", "recommendation"]
    channel_slug: Optional[str] = None
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
