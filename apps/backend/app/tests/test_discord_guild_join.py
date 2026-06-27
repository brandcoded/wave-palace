"""Tests for Discord guild-join behaviour added to the OAuth callback.

Covers:
- /initiate includes guilds.join in the scope param
- _add_user_to_guild issues the right PUT with bot auth + user token
- 201 (newly added) is treated as success
- 204 (already a member) is treated as success
- A non-2xx guild-join response does NOT break the follow (no 500)
- A network error in the guild call is swallowed
- DISCORD_GUILD_ID unset skips the join silently
- Full /callback flow: guild-join called and follow completes
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.routes.auth_discord import _add_user_to_guild
from app.main import app

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-long!"
_GUILD_ID = "111222333444555666"
_BOT_TOKEN = "test-bot-token"
_USER_TOKEN = "user-access-token-abc"
_DISCORD_USER_ID = "987654321012345678"
_DISCORD_USERNAME = "TestFollower"
_CODE = "ABCDEF"


def _make_state(intent: str = "follow", wp_code: str = _CODE) -> str:
    import os
    os.environ["JWT_SECRET"] = _JWT_SECRET
    from app.api.routes.auth_discord import _make_state_token
    return _make_state_token(intent, wp_code=wp_code)


# ---------------------------------------------------------------------------
# /initiate — scope must include guilds.join
# ---------------------------------------------------------------------------

def test_initiate_scope_includes_guilds_join(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "client-id-123")
    monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://wavepalace.live/callback")
    monkeypatch.setenv("JWT_SECRET", _JWT_SECRET)

    client = TestClient(app, follow_redirects=False)
    res = client.get("/api/auth/discord/initiate?intent=follow&code=ABCDEF")

    assert res.status_code in (302, 307)
    qs = parse_qs(urlparse(res.headers["location"]).query)
    scopes = qs.get("scope", [""])[0].split()
    assert "identify" in scopes
    assert "guilds.join" in scopes


# ---------------------------------------------------------------------------
# _add_user_to_guild unit tests (no HTTP, fully mocked client)
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously (no pytest-asyncio needed)."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_mock_client(status: int, json_body: dict | None = None) -> httpx.AsyncClient:
    """Return an AsyncClient whose put() resolves to a canned response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    response.text = json.dumps(json_body) if json_body else ""
    mock_client.put = AsyncMock(return_value=response)
    return mock_client


def test_add_user_to_guild_201_calls_correct_url():
    client = _make_mock_client(201)
    _run(_add_user_to_guild(client, _GUILD_ID, _DISCORD_USER_ID, _BOT_TOKEN, _USER_TOKEN))

    client.put.assert_awaited_once()
    call_kwargs = client.put.await_args
    url = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("url", "")
    assert _GUILD_ID in url
    assert _DISCORD_USER_ID in url
    headers = call_kwargs.kwargs.get("headers", {})
    assert headers.get("Authorization") == f"Bot {_BOT_TOKEN}"
    body = call_kwargs.kwargs.get("json", {})
    assert body.get("access_token") == _USER_TOKEN


def test_add_user_to_guild_204_no_raise():
    client = _make_mock_client(204)
    _run(_add_user_to_guild(client, _GUILD_ID, _DISCORD_USER_ID, _BOT_TOKEN, _USER_TOKEN))
    client.put.assert_awaited_once()


def test_add_user_to_guild_403_is_swallowed_no_raise(caplog):
    client = _make_mock_client(403, {"code": 50013, "message": "Missing Permissions"})
    with caplog.at_level(logging.WARNING, logger="wavepalace.auth.discord"):
        _run(_add_user_to_guild(client, _GUILD_ID, _DISCORD_USER_ID, _BOT_TOKEN, _USER_TOKEN))
    assert any("guild-join failed" in r.message for r in caplog.records)


def test_add_user_to_guild_network_error_swallowed(caplog):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.put = AsyncMock(side_effect=httpx.ConnectError("refused"))
    with caplog.at_level(logging.WARNING, logger="wavepalace.auth.discord"):
        _run(_add_user_to_guild(mock_client, _GUILD_ID, _DISCORD_USER_ID, _BOT_TOKEN, _USER_TOKEN))
    assert any("guild-join request raised" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# /callback integration — guild-join wired end-to-end
# ---------------------------------------------------------------------------

def _env_for_callback(monkeypatch, *, guild_id: str | None = _GUILD_ID) -> None:
    monkeypatch.setenv("DISCORD_CLIENT_ID", "client-id")
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://wavepalace.live/callback")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", _BOT_TOKEN)
    monkeypatch.setenv("JWT_SECRET", _JWT_SECRET)
    if guild_id is not None:
        monkeypatch.setenv("DISCORD_GUILD_ID", guild_id)
    else:
        monkeypatch.delenv("DISCORD_GUILD_ID", raising=False)


def _wire_deps(follow_svc=None, auth_svc=None):
    from datetime import datetime, timezone

    from app.api.dependencies import get_follow_service, get_auth_service
    from app.repositories.channel_repository import SeedChannelRepository
    from app.repositories.code_repository import SeedCodeRepository
    from app.repositories.follow_repository import SeedFollowRepository
    from app.repositories.user_repository import SeedUserRepository
    from app.repositories.session_repository import SeedSessionRepository
    from app.schemas.code import CodeDocument
    from app.services.follow_service import FollowService
    from app.services.auth_service import AuthService

    if follow_svc is None:
        code_repo = SeedCodeRepository()
        _run(code_repo.create(CodeDocument(
            code=_CODE,
            channel_slug="late-night-house",
            entity_type="channel",
            entity_id="late-night-house",
            created_at=datetime.now(tz=timezone.utc),
            active=True,
        )))
        follow_svc = FollowService(
            SeedFollowRepository(), code_repo, SeedChannelRepository()
        )
    if auth_svc is None:
        auth_svc = AuthService(SeedUserRepository(), SeedSessionRepository())

    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    app.dependency_overrides[get_auth_service] = lambda: auth_svc


def _make_discord_client_mock(guild_status: int = 201):
    """Build an AsyncMock httpx.AsyncClient factory with pre-set Discord responses.

    Returns (mock_cls, main_instance, guild_instance) so callers can inspect calls.
    """
    token_res = MagicMock(spec=httpx.Response)
    token_res.status_code = 200
    token_res.json = MagicMock(return_value={"access_token": _USER_TOKEN, "token_type": "Bearer"})

    me_res = MagicMock(spec=httpx.Response)
    me_res.status_code = 200
    me_res.json = MagicMock(return_value={"id": _DISCORD_USER_ID, "username": _DISCORD_USERNAME, "avatar": None})

    guild_res = MagicMock(spec=httpx.Response)
    guild_res.status_code = guild_status
    guild_res.text = ""

    main_client = AsyncMock()
    main_client.post = AsyncMock(return_value=token_res)
    main_client.get = AsyncMock(return_value=me_res)
    main_client.__aenter__ = AsyncMock(return_value=main_client)
    main_client.__aexit__ = AsyncMock(return_value=False)

    guild_client = AsyncMock()
    guild_client.put = AsyncMock(return_value=guild_res)
    guild_client.__aenter__ = AsyncMock(return_value=guild_client)
    guild_client.__aexit__ = AsyncMock(return_value=False)

    mock_cls = MagicMock(side_effect=[main_client, guild_client])
    return mock_cls, main_client, guild_client


def test_callback_guild_join_201_follow_completes(monkeypatch):
    _env_for_callback(monkeypatch)
    _wire_deps()
    state = _make_state()
    mock_cls, _main, guild_instance = _make_discord_client_mock(guild_status=201)

    # Patch get_settings so discord_guild_id is seen at call time (frozen dataclass
    # reads env vars at class-definition time, not instantiation time).
    from app.core.config import Settings
    fake_settings = Settings.__new__(Settings)
    object.__setattr__(fake_settings, "discord_guild_id", _GUILD_ID)
    object.__setattr__(fake_settings, "discord_bot_token", _BOT_TOKEN)
    object.__setattr__(fake_settings, "frontend_origin", "http://localhost:3000")

    with (
        patch("app.api.routes.auth_discord.httpx.AsyncClient", mock_cls),
        patch("app.api.routes.auth_discord.get_settings", return_value=fake_settings),
    ):
        res = TestClient(app, follow_redirects=False).get(
            f"/api/auth/discord/callback?code=dc-code&state={state}"
        )

    app.dependency_overrides.clear()

    assert res.status_code in (302, 307)
    assert "follows" in res.headers["location"]
    assert mock_cls.call_count == 2  # one for token+user, one for guild
    guild_instance.put.assert_awaited_once()
    put_call = guild_instance.put.await_args
    headers = put_call.kwargs.get("headers", {})
    assert headers.get("Authorization") == f"Bot {_BOT_TOKEN}"
    body = put_call.kwargs.get("json", {})
    assert body.get("access_token") == _USER_TOKEN


def test_callback_guild_join_204_already_member(monkeypatch):
    _env_for_callback(monkeypatch)
    _wire_deps()
    state = _make_state()
    mock_cls, _, _ = _make_discord_client_mock(guild_status=204)

    with patch("app.api.routes.auth_discord.httpx.AsyncClient", mock_cls):
        res = TestClient(app, follow_redirects=False).get(
            f"/api/auth/discord/callback?code=dc-code&state={state}"
        )

    app.dependency_overrides.clear()

    assert res.status_code in (302, 307)
    assert "follows" in res.headers["location"]


def test_callback_guild_join_failure_does_not_500(monkeypatch):
    """403 from guild endpoint must NOT propagate — follow still completes."""
    _env_for_callback(monkeypatch)
    _wire_deps()
    state = _make_state()
    mock_cls, _, _ = _make_discord_client_mock(guild_status=403)

    with patch("app.api.routes.auth_discord.httpx.AsyncClient", mock_cls):
        res = TestClient(app, follow_redirects=False).get(
            f"/api/auth/discord/callback?code=dc-code&state={state}"
        )

    app.dependency_overrides.clear()

    assert res.status_code in (302, 307)
    assert "follows" in res.headers["location"]


def test_callback_no_guild_id_skips_join(monkeypatch):
    """When DISCORD_GUILD_ID is unset, no guild PUT is issued."""
    _env_for_callback(monkeypatch, guild_id=None)
    _wire_deps()
    state = _make_state()

    # Only ONE AsyncClient is created (no guild join)
    token_res = MagicMock(spec=httpx.Response)
    token_res.status_code = 200
    token_res.json = MagicMock(return_value={"access_token": _USER_TOKEN, "token_type": "Bearer"})
    me_res = MagicMock(spec=httpx.Response)
    me_res.status_code = 200
    me_res.json = MagicMock(return_value={"id": _DISCORD_USER_ID, "username": _DISCORD_USERNAME, "avatar": None})
    main_client = AsyncMock()
    main_client.post = AsyncMock(return_value=token_res)
    main_client.get = AsyncMock(return_value=me_res)
    main_client.__aenter__ = AsyncMock(return_value=main_client)
    main_client.__aexit__ = AsyncMock(return_value=False)
    mock_cls = MagicMock(return_value=main_client)

    with patch("app.api.routes.auth_discord.httpx.AsyncClient", mock_cls):
        res = TestClient(app, follow_redirects=False).get(
            f"/api/auth/discord/callback?code=dc-code&state={state}"
        )

    app.dependency_overrides.clear()

    assert res.status_code in (302, 307)
    assert mock_cls.call_count == 1  # no second call for guild join
    main_client.put.assert_not_called()
