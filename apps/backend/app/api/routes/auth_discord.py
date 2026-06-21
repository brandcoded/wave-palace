"""Discord OAuth routes for listener identity (Slice 9)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_follow_service
from app.schemas.follow import FollowSubmitRequest
from app.services.follow_service import FollowService

router = APIRouter(prefix="/api/auth/discord", tags=["auth-discord"])

logger = logging.getLogger("wavepalace.auth.discord")

_ALGORITHM = "HS256"
_STATE_TTL_MINUTES = 10
_LISTENER_COOKIE_DAYS = 30


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")


def _make_state_token(wp_code: str) -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES)
    return jwt.encode(
        {"wp_code": wp_code, "type": "discord_state", "exp": exp},
        _jwt_secret(),
        algorithm=_ALGORITHM,
    )


def _decode_state_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
        if payload.get("type") != "discord_state":
            raise ValueError("Wrong token type")
        return payload
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


@router.get("/initiate")
async def discord_initiate(
    code: str = Query(..., alias="code"),
) -> RedirectResponse:
    client_id = os.getenv("DISCORD_CLIENT_ID")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Discord OAuth is not configured")
    state = _make_state_token(code)
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    })
    return RedirectResponse(url=f"https://discord.com/oauth2/authorize?{params}")


@router.get("/callback")
async def discord_callback(
    code: str = Query(...),
    state: str = Query(...),
    follow_svc: FollowService = Depends(get_follow_service),
) -> RedirectResponse:
    state_data = _decode_state_token(state)
    wp_code = state_data["wp_code"]

    client_id = os.getenv("DISCORD_CLIENT_ID")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=503, detail="Discord OAuth is not configured")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Discord token exchange failed")
        access_token = token_res.json()["access_token"]

        me_res = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if me_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Discord user fetch failed")
        me = me_res.json()

    discord_user_id = me["id"]
    discord_username = me["username"]

    try:
        await follow_svc.submit_follow(
            code=wp_code,
            request=FollowSubmitRequest(
                channel="discord",
                discord_user_id=discord_user_id,
                discord_username=discord_username,
            ),
        )
    except HTTPException as exc:
        if exc.status_code != 409:
            raise  # Already following is OK — just set cookie and continue

    frontend_origin = (
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")[0].strip()
    )
    response = RedirectResponse(url=f"{frontend_origin}/follows")
    response.set_cookie(
        "wp_listener_discord_id",
        discord_user_id,
        httponly=True,
        max_age=_LISTENER_COOKIE_DAYS * 86400,
        samesite="lax",
    )
    return response
