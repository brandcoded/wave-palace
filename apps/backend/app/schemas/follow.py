"""Schemas for the Follow Intent system (Slice 9)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

NotificationChannel = Literal["discord", "email", "browser_push", "sms"]


class FollowDocument(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    channel_slug: str
    notification_channel: NotificationChannel
    discord_user_id: Optional[str] = None
    discord_username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    push_subscription: Optional[dict] = None
    vrchat_username: Optional[str] = None
    confirmed: bool = False
    created_at: datetime
    code_used: str


class FollowSubmitRequest(BaseModel):
    channel: NotificationChannel
    discord_user_id: Optional[str] = None
    discord_username: Optional[str] = None
    email: Optional[str] = None
    push_subscription: Optional[dict] = None
    vrchat_username: Optional[str] = None


class FollowResponse(BaseModel):
    follow_id: str
    channel: str
    confirmed: bool


class FollowPublicView(BaseModel):
    id: str
    entity_type: str
    channel_slug: str
    display_name: str
    notification_channel: str
    confirmed: bool
    created_at: datetime
