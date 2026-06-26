"""Schemas for the Follow Intent system (Slice 9 + 13)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, model_validator

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
    # code_used is required for new follows; default="" so pre-Slice-9 docs in
    # MongoDB that were inserted without this field still deserialize without error.
    code_used: str = ""
    # Slice 13 — notification preferences (backfilled for pre-Slice-13 documents)
    notify_new_tracks: bool = True
    notify_channel_live: bool = True
    notify_digest: bool = False

    @model_validator(mode="before")
    @classmethod
    def _backfill_legacy_fields(cls, values: object) -> object:
        if isinstance(values, dict):
            values.setdefault("notify_new_tracks", True)
            values.setdefault("notify_channel_live", True)
            values.setdefault("notify_digest", False)
            values.setdefault("code_used", "")
        return values


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
    notify_new_tracks: bool = True
    notify_channel_live: bool = True
    notify_digest: bool = False
