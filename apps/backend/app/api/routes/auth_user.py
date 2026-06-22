"""User auth routes — email magic link, password, /me, /logout (Slice 10)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.dependencies import get_auth_service
from app.core.auth import get_current_user
from app.schemas.user import UserDocument
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

_SESSION_COOKIE = "wp_session"


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


# ---------------------------------------------------------------------------
# Email magic link
# ---------------------------------------------------------------------------

class EmailRequestBody(BaseModel):
    email: str


@router.post("/email/request", status_code=200)
async def request_email_link(
    body: EmailRequestBody,
    request: Request,
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    """Send a magic sign-in link. Always returns 200 — no email enumeration."""
    base_url = str(request.base_url).rstrip("/")
    await auth_svc.issue_email_token(body.email, base_url)
    return {"ok": True, "message": "If that email is registered, a sign-in link is on its way."}


@router.get("/email/verify")
async def verify_email_link(
    token: str,
    response: Response,
    auth_svc: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Verify a magic-link token, issue session, redirect to admin."""
    user = await auth_svc.verify_email_token(token)
    session_id = await auth_svc.issue_session(user)
    frontend_origin = (
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")[0].strip()
    )
    redirect = RedirectResponse(url=f"{frontend_origin}/admin/submissions")
    redirect.set_cookie(
        key=_SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=30 * 86400,
        path="/",
    )
    return redirect


# ---------------------------------------------------------------------------
# Password auth
# ---------------------------------------------------------------------------

class RegisterBody(BaseModel):
    email: str
    password: str
    display_name: str


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
async def register(
    body: RegisterBody,
    response: Response,
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    user = await auth_svc.register(body.email, body.password, body.display_name)
    session_id = await auth_svc.issue_session(user)
    _set_session_cookie(response, session_id)
    return {"id": user.id, "display_name": user.display_name, "roles": user.roles}


@router.post("/login")
async def login(
    body: LoginBody,
    response: Response,
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    user = await auth_svc.password_login(body.email, body.password)
    session_id = await auth_svc.issue_session(user)
    _set_session_cookie(response, session_id)
    return {"id": user.id, "display_name": user.display_name, "roles": user.roles}


# ---------------------------------------------------------------------------
# Session / identity
# ---------------------------------------------------------------------------

@router.get("/me")
async def me(user: UserDocument = Depends(get_current_user)) -> dict:
    from app.core.config import get_settings
    return {
        "id": user.id,
        "display_name": user.display_name,
        "roles": user.roles,
        "avatar_url": user.avatar_url,
        "email": user.email,
        "seedMode": get_settings().use_seed_mode,
    }


@router.post("/logout")
async def logout(
    response: Response,
    wp_session: str | None = Cookie(default=None),
    auth_svc: AuthService = Depends(get_auth_service),
) -> dict:
    if wp_session:
        await auth_svc.revoke_session(wp_session)
    response.delete_cookie(key=_SESSION_COOKIE, path="/", samesite="none", secure=True)
    response.delete_cookie(key="wp_admin_token", path="/", samesite="none", secure=True)
    return {"ok": True}
