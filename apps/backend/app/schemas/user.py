"""User and auth token schemas for Slice 10 — Identity & Roles."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

UserRole = Literal["admin", "music_director"]

BOOTSTRAP_ADMIN_ID = "admin-bootstrap"


class UserDocument(BaseModel):
    id: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: str
    avatar_url: Optional[str] = None
    roles: list[UserRole] = []
    password_hash: Optional[str] = None
    discord_user_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    is_active: bool = True


class UserPublic(BaseModel):
    id: str
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    roles: list[UserRole]
    is_active: bool
    discord_user_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class SessionDocument(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False


class EmailLoginTokenDocument(BaseModel):
    id: str
    token_hash: str
    email: str
    expires_at: datetime
    consumed: bool = False
