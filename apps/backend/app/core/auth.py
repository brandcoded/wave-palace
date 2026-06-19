"""Admin authentication helpers — single-admin JWT via httpOnly cookie."""

from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, HTTPException, Request

logger = logging.getLogger("wavepalace.auth")

_ALGORITHM = "HS256"
_TOKEN_TTL_HOURS = 24
_COOKIE_NAME = "wp_admin_token"


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        logger.warning("JWT_SECRET not set — using insecure default. Set it in production.")
        return "dev-jwt-secret-change-me"
    return secret


def _admin_secret() -> str:
    secret = os.getenv("ADMIN_SECRET", "changeme")
    if secret == "changeme":
        logger.warning("ADMIN_SECRET is set to the default 'changeme'. Change it in production.")
    return secret


def verify_secret(candidate: str) -> bool:
    """Constant-time compare of candidate against ADMIN_SECRET."""
    return hmac.compare_digest(candidate.encode(), _admin_secret().encode())


def create_token() -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    return jwt.encode({"sub": "admin", "exp": exp}, _jwt_secret(), algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])


def get_current_admin(
    wp_admin_token: str | None = Cookie(default=None),
) -> dict:
    """FastAPI Depends() — raises 401 if cookie is missing or JWT invalid/expired."""
    if not wp_admin_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = _decode_token(wp_admin_token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
