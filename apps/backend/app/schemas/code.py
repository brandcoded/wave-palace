"""Schemas for the Code Capture system (Slice 9)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CodeDocument(BaseModel):
    code: str
    channel_slug: str
    entity_type: str = "channel"
    entity_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    active: bool = True


class CodeCreateRequest(BaseModel):
    channel_slug: str
    entity_type: str = "channel"
    entity_id: str
    expires_at: Optional[datetime] = None


class CodePublicResponse(BaseModel):
    code: str
    entity_type: str
    entity_id: str
    display_name: str
    host_name: Optional[str] = None
    genre: Optional[list[str]] = None
    mood: Optional[list[str]] = None
    cover_image_url: Optional[str] = None
