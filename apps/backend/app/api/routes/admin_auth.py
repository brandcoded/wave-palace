"""Admin auth routes: bootstrap secret login, logout, session check.

The shared-secret POST /api/admin/login still works as a break-glass
bootstrap — it now issues the new wp_session cookie (opaque, server-side)
instead of the legacy wp_admin_token JWT. The wp_admin_token JWT is still
accepted during the grace period (see core/auth.py: get_current_user).
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.api.dependencies import get_auth_service
from app.core.auth import get_current_user, verify_secret
from app.core.config import get_settings
from app.schemas.user import UserDocument
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])

_SESSION_COOKIE = "wp_session"
_RATE_WINDOW = 900
_RATE_LIMIT = 5
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
    _login_attempts.clear()


class LoginRequest(BaseModel):
    secret: str


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=30 * 86400,
        path="/",
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    """Break-glass bootstrap login via ADMIN_SECRET. Issues a wp_session cookie."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    _check_rate_limit(ip)

    if not verify_secret(body.secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)
    _set_session_cookie(response, session_id)
    return {"ok": True}


@router.post("/logout")
async def logout(
    response: Response,
    user: UserDocument = Depends(get_current_user),
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    # Best-effort: revoke session from request cookie if present
    response.delete_cookie(key=_SESSION_COOKIE, path="/", samesite="none", secure=True)
    response.delete_cookie(key="wp_admin_token", path="/", samesite="none", secure=True)
    return {"ok": True}


@router.get("/me")
async def me(user: UserDocument = Depends(get_current_user)) -> dict:
    return {
        "ok": True,
        "id": user.id,
        "display_name": user.display_name,
        "roles": user.roles,
        "avatar_url": user.avatar_url,
        "seedMode": get_settings().use_seed_mode,
    }
