"""Channel invite token schema for Slice 11 — Host Onboarding & Ownership."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChannelInviteToken(BaseModel):
    id: str                                  # uuid
    token_hash: str                          # SHA-256 of the raw token (raw never stored)
    channel_slug: str
    created_by_user_id: str
    created_at: datetime
    expires_at: datetime                     # 7 days from creation
    consumed: bool = False
    consumed_by_user_id: Optional[str] = None
    consumed_at: Optional[datetime] = None


class ChannelInvitePublic(BaseModel):
    """Invite metadata safe to list to an admin — never includes the raw token."""

    id: str
    channel_slug: str
    created_by_user_id: str
    created_at: datetime
    expires_at: datetime
    consumed: bool
    consumed_by_user_id: Optional[str] = None
    consumed_at: Optional[datetime] = None
