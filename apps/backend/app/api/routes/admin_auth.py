"""Admin auth routes: login, logout, session check."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.core.auth import create_token, get_current_admin, verify_secret

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])

_COOKIE_NAME = "wp_admin_token"
_RATE_WINDOW = 900   # 15 minutes
_RATE_LIMIT = 5

# Simple in-memory rate limiter: {ip: [timestamp, ...]}
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - _RATE_WINDOW
    attempts = [t for t in _login_attempts[ip] if t > window_start]
    _login_attempts[ip] = attempts
    if len(attempts) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    _login_attempts[ip].append(now)


def reset_rate_limits() -> None:
    """Test helper to clear rate limit state."""
    _login_attempts.clear()


class LoginRequest(BaseModel):
    secret: str


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _check_rate_limit(ip)

    if not verify_secret(body.secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = create_token()
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=86400,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(key=_COOKIE_NAME, path="/", samesite="none", secure=True)
    return {"ok": True}


@router.get("/me")
async def me(_: dict = Depends(get_current_admin)) -> dict:
    return {"ok": True}
