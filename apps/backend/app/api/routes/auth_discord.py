"""Discord OAuth routes — follow intent (Slice 9) and login intent (Slice 10)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_auth_service, get_follow_service
from app.core.config import get_settings
from app.schemas.follow import FollowSubmitRequest
from app.services.auth_service import AuthService
from app.services.follow_service import FollowService

router = APIRouter(prefix="/api/auth/discord", tags=["auth-discord"])

logger = logging.getLogger("wavepalace.auth.discord")

_ALGORITHM = "HS256"
_STATE_TTL_MINUTES = 10
_LISTENER_COOKIE_DAYS = 30
_SESSION_COOKIE = "wp_session"


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")


def _make_state_token(intent: str, wp_code: str | None = None) -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES)
    payload: dict = {"intent": intent, "type": "discord_state", "exp": exp}
    if wp_code:
        payload["wp_code"] = wp_code
    return jwt.encode(payload, _jwt_secret(), algorithm=_ALGORITHM)


def _decode_state_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
        if payload.get("type") != "discord_state":
            raise ValueError("Wrong token type")
        return payload
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


def _get_discord_config():
    client_id = os.getenv("DISCORD_CLIENT_ID")
    redirect_uri = os.getenv("DISCORD_REDIRECT_URI")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Discord OAuth is not configured")
    return client_id, redirect_uri, client_secret


@router.get("/initiate")
async def discord_initiate(
    code: str = Query(default=None, alias="code"),
    intent: str = Query(default="follow"),
) -> RedirectResponse:
    """
    Start Discord OAuth flow.
    - intent=follow (default): requires wp_code follow code
    - intent=login: admin/user login
    """
    if intent == "follow" and not code:
        raise HTTPException(status_code=400, detail="Follow intent requires a channel code")

    client_id, redirect_uri, _ = _get_discord_config()
    state = _make_state_token(intent, wp_code=code)
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify guilds.join",
        "state": state,
    })
    return RedirectResponse(url=f"https://discord.com/oauth2/authorize?{params}")


async def _add_user_to_guild(
    http_client: httpx.AsyncClient,
    guild_id: str,
    discord_user_id: str,
    bot_token: str,
    user_access_token: str,
) -> None:
    """PUT the user into the WavePalace Discord server so bot DMs work.

    201 = newly added, 204 = already a member — both are success.
    All failures are logged as warnings and swallowed so the follow
    never breaks due to a guild-join error.
    """
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{discord_user_id}"
    try:
        res = await http_client.put(
            url,
            json={"access_token": user_access_token},
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
        )
        if res.status_code not in (201, 204):
            logger.warning(
                "Discord guild-join failed for user %s: HTTP %s — %s",
                discord_user_id,
                res.status_code,
                res.text[:200],
            )
    except Exception:
        logger.warning(
            "Discord guild-join request raised an exception for user %s",
            discord_user_id,
            exc_info=True,
        )


@router.get("/callback")
async def discord_callback(
    code: str = Query(...),
    state: str = Query(...),
    follow_svc: FollowService = Depends(get_follow_service),
    auth_svc: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    state_data = _decode_state_token(state)
    intent = state_data.get("intent", "follow")
    wp_code = state_data.get("wp_code")

    client_id, redirect_uri, client_secret = _get_discord_config()
    if not client_secret:
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
        me_data = me_res.json()

    discord_user_id = me_data["id"]
    discord_username = me_data["username"]
    avatar_hash = me_data.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_user_id}/{avatar_hash}.png"
        if avatar_hash else None
    )

    # Auto-add the user to the WavePalace server so bot DMs always work.
    # Requires DISCORD_GUILD_ID + the bot already being a member of that server.
    settings = get_settings()
    if settings.discord_guild_id and settings.discord_bot_token:
        async with httpx.AsyncClient() as guild_client:
            await _add_user_to_guild(
                guild_client,
                guild_id=settings.discord_guild_id,
                discord_user_id=discord_user_id,
                bot_token=settings.discord_bot_token,
                user_access_token=access_token,
            )
    else:
        logger.debug(
            "DISCORD_GUILD_ID or DISCORD_BOT_TOKEN not set — skipping guild auto-join for user %s",
            discord_user_id,
        )

    frontend_origin = (
        os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").split(",")[0].strip()
    )

    if intent == "login":
        # Identity + session for admin/user login
        user = await auth_svc.find_or_create_by_discord(
            discord_user_id, discord_username, avatar_url
        )
        session_id = await auth_svc.issue_session(user)
        response = RedirectResponse(url=f"{frontend_origin}/admin/submissions")
        response.set_cookie(
            _SESSION_COOKIE,
            session_id,
            httponly=True,
            max_age=30 * 86400,
            samesite="none",
            secure=True,
            path="/",
        )
        return response

    # intent == "follow" (Slice 9 behaviour preserved)
    if not wp_code:
        raise HTTPException(status_code=400, detail="Missing follow code")

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
            raise

    response = RedirectResponse(url=f"{frontend_origin}/follows")
    response.set_cookie(
        "wp_listener_discord_id",
        discord_user_id,
        httponly=True,
        max_age=_LISTENER_COOKIE_DAYS * 86400,
        samesite="lax",
    )
    return response
