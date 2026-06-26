"""Auth helpers — get_current_user, require_roles, and legacy shims (Slice 10)."""

from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, Path

from app.api.dependencies import get_auth_service, get_channel_service
from app.schemas.channel import Channel
from app.schemas.user import UserDocument

logger = logging.getLogger("wavepalace.auth")

_ALGORITHM = "HS256"
_TOKEN_TTL_HOURS = 24
_COOKIE_NAME = "wp_admin_token"
_SESSION_COOKIE = "wp_session"


# ---------------------------------------------------------------------------
# Utility — keep these for legacy login and tests
# ---------------------------------------------------------------------------

def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        logger.warning("JWT_SECRET not set — using insecure default.")
        return "dev-jwt-secret-change-me"
    return secret


def _admin_secret() -> str:
    return os.getenv("ADMIN_SECRET", "changeme")


def verify_secret(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode(), _admin_secret().encode())


def create_token() -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    return jwt.encode({"sub": "admin", "exp": exp}, _jwt_secret(), algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])


# ---------------------------------------------------------------------------
# New: opaque session + role-based guards
# ---------------------------------------------------------------------------

async def get_current_user(
    wp_session: Optional[str] = Cookie(default=None),
    wp_admin_token: Optional[str] = Cookie(default=None),
    auth_service=Depends(get_auth_service),
) -> UserDocument:
    """
    FastAPI Depends() — returns the authenticated UserDocument.

    Checks wp_session first (new opaque sessions), then falls back to the
    legacy wp_admin_token JWT (grace period for in-flight sessions across deploy).
    """
    if wp_session:
        user = await auth_service.get_user_by_session(wp_session)
        if user and user.is_active:
            return user

    # Grace period: accept legacy wp_admin_token
    if wp_admin_token:
        try:
            payload = _decode_token(wp_admin_token)
            if payload.get("sub") == "admin":
                user = await auth_service.get_or_create_bootstrap_admin()
                if user.is_active:
                    return user
        except jwt.InvalidTokenError:
            pass

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_optional_user(
    wp_session: Optional[str] = Cookie(default=None),
    wp_admin_token: Optional[str] = Cookie(default=None),
    auth_service=Depends(get_auth_service),
) -> Optional[UserDocument]:
    """Like get_current_user but returns None when unauthenticated."""
    if wp_session:
        user = await auth_service.get_user_by_session(wp_session)
        if user and user.is_active:
            return user
    if wp_admin_token:
        try:
            payload = _decode_token(wp_admin_token)
            if payload.get("sub") == "admin":
                user = await auth_service.get_or_create_bootstrap_admin()
                if user.is_active:
                    return user
        except jwt.InvalidTokenError:
            pass
    return None


def require_roles(*roles: str):
    """
    Factory returning a FastAPI dependency that enforces role membership.
    Usage in routes: _: UserDocument = Depends(require_roles("admin"))
    """
    async def _dep(user: UserDocument = Depends(get_current_user)) -> UserDocument:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        if not any(r in user.roles for r in roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dep


# Shim: existing route files use Depends(get_current_admin) — unchanged.
get_current_admin = require_roles("admin", "music_director")


# ---------------------------------------------------------------------------
# Slice 11 — ownership-scoped guard
# ---------------------------------------------------------------------------

def require_channel_owner(slug_param: str = "slug"):
    """
    Factory returning a dependency that resolves the channel from the path and
    enforces that the caller owns it. Admin and music_director bypass the
    ownership check (they can act on any channel).

    Returns a (UserDocument, Channel) tuple so routes get both without a second
    lookup.
    """
    async def _dep(
        slug: str = Path(..., alias=slug_param),
        user: UserDocument = Depends(get_current_user),
        channel_service=Depends(get_channel_service),
    ) -> tuple[UserDocument, Channel]:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        raw = await channel_service.get_raw_by_slug(slug)
        if raw is None:
            raise HTTPException(status_code=404, detail="Channel not found")
        if "admin" in user.roles or "music_director" in user.roles:
            return user, Channel.model_validate(raw)
        if user.id not in (raw.get("owner_ids") or []):
            raise HTTPException(status_code=403, detail="Not an owner of this channel")
        return user, Channel.model_validate(raw)

    return _dep
