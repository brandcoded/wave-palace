"""Tests for Slice 9 — Code Capture + Follow Intent + Notification Stack."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_code_service, get_follow_service
from app.api.routes import admin_auth as auth_routes
from app.core.auth import create_token
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.code_repository import CodeRepository, SeedCodeRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.schemas.code import CodeDocument
from app.services.code_service import CodeService
from app.services.follow_service import FollowService, make_confirm_token
from app.services.notification_service import NotificationService

_SECRET = "test-secret-xyzzy-very-long-for-hmac-minimum"
_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-long!"


@pytest.fixture(autouse=True)
def _patch_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", _SECRET)
    monkeypatch.setenv("JWT_SECRET", _JWT_SECRET)
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


@pytest.fixture()
def repos():
    code_repo = SeedCodeRepository()
    follow_repo = SeedFollowRepository()
    channel_repo = SeedChannelRepository()
    return code_repo, follow_repo, channel_repo


@pytest.fixture()
def slice9_client(repos):
    code_repo, follow_repo, channel_repo = repos
    code_svc = CodeService(code_repo, channel_repo)
    follow_svc = FollowService(follow_repo, code_repo, channel_repo)
    app.dependency_overrides[get_code_service] = lambda: code_svc
    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    c = TestClient(app, raise_server_exceptions=True)
    c.cookies.set("wp_admin_token", create_token())
    yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Admin code management
# ---------------------------------------------------------------------------

def test_admin_create_code_returns_201(slice9_client):
    res = slice9_client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "abc"},
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["code"]) == 6
    assert data["code"].isupper() or data["code"].isalnum()
    assert data["active"] is True
    assert data["channel_slug"] == "late-night-house"


def test_admin_list_codes(slice9_client):
    slice9_client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "abc"},
    )
    res = slice9_client.get("/api/admin/codes")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_admin_deactivate_code(slice9_client):
    create = slice9_client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "abc"},
    )
    code = create.json()["code"]
    res = slice9_client.delete(f"/api/admin/codes/{code}")
    assert res.status_code == 204
    # Code should now resolve as 404
    resolved = slice9_client.get(f"/api/codes/{code}")
    assert resolved.status_code == 404


def test_admin_deactivate_nonexistent_code_returns_404(slice9_client):
    res = slice9_client.delete("/api/admin/codes/XXXXXX")
    assert res.status_code == 404


def test_admin_codes_requires_auth(slice9_client):
    c = TestClient(app)  # no auth cookie
    res = c.get("/api/admin/codes")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Public code resolution
# ---------------------------------------------------------------------------

def test_resolve_active_code_returns_channel_info(slice9_client):
    create = slice9_client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "ch1"},
    )
    code = create.json()["code"]
    res = slice9_client.get(f"/api/codes/{code}")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == code
    assert data["display_name"] == "Late Night House"
    assert data["host_name"] is not None


def test_resolve_inactive_code_returns_404(slice9_client):
    create = slice9_client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "ch1"},
    )
    code = create.json()["code"]
    slice9_client.delete(f"/api/admin/codes/{code}")
    res = slice9_client.get(f"/api/codes/{code}")
    assert res.status_code == 404
    assert "no longer active" in res.json()["detail"]


def test_resolve_unknown_code_returns_404(slice9_client):
    res = slice9_client.get("/api/codes/XXXXXX")
    assert res.status_code == 404


def test_resolve_expired_code_returns_404(repos):
    import asyncio
    code_repo, follow_repo, channel_repo = repos
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    expired_doc = CodeDocument(
        code="EXPIRY",
        channel_slug="late-night-house",
        entity_type="channel",
        entity_id="ch1",
        created_at=datetime.now(tz=timezone.utc),
        expires_at=past,
        active=True,
    )
    asyncio.run(code_repo.create(expired_doc))

    code_svc = CodeService(code_repo, channel_repo)
    follow_svc = FollowService(follow_repo, code_repo, channel_repo)
    app.dependency_overrides[get_code_service] = lambda: code_svc
    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    c = TestClient(app)
    try:
        res = c.get("/api/codes/EXPIRY")
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Follow submission
# ---------------------------------------------------------------------------

def _make_code(client) -> str:
    res = client.post(
        "/api/admin/codes",
        json={"channel_slug": "late-night-house", "entity_type": "channel", "entity_id": "ch1"},
    )
    return res.json()["code"]


def test_discord_follow_creates_confirmed_follow(slice9_client):
    code = _make_code(slice9_client)
    res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "discord", "discord_user_id": "123456789", "discord_username": "TestUser"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["channel"] == "discord"
    assert data["confirmed"] is True
    assert data["follow_id"]


def test_email_follow_creates_unconfirmed_follow(slice9_client):
    code = _make_code(slice9_client)
    res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "email", "email": "listener@example.com"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["channel"] == "email"
    assert data["confirmed"] is False


def test_duplicate_follow_returns_409(slice9_client):
    code = _make_code(slice9_client)
    slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "discord", "discord_user_id": "999", "discord_username": "Dup"},
    )
    res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "discord", "discord_user_id": "999", "discord_username": "Dup"},
    )
    assert res.status_code == 409


def test_follow_inactive_code_returns_404(slice9_client):
    code = _make_code(slice9_client)
    slice9_client.delete(f"/api/admin/codes/{code}")
    res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "discord", "discord_user_id": "111"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Email confirmation
# ---------------------------------------------------------------------------

def test_email_confirm_valid_token_sets_confirmed(slice9_client, repos):
    code_repo, follow_repo, channel_repo = repos
    code = _make_code(slice9_client)
    follow_res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "email", "email": "confirm@example.com"},
    )
    follow_id = follow_res.json()["follow_id"]

    token = make_confirm_token(follow_id, "confirm@example.com")
    res = slice9_client.post(f"/api/follows/confirm?token={token}")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_email_confirm_expired_token_returns_400(slice9_client, repos):
    code_repo, follow_repo, channel_repo = repos
    # Build an already-expired token
    past = datetime.now(tz=timezone.utc) - timedelta(hours=25)
    token = jwt.encode(
        {"follow_id": "x", "email": "x@x.com", "type": "email_confirm", "exp": past},
        _JWT_SECRET,
        algorithm="HS256",
    )
    res = slice9_client.post(f"/api/follows/confirm?token={token}")
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Follow management (listener identity via cookie)
# ---------------------------------------------------------------------------

def test_delete_follow_returns_204(slice9_client):
    code = _make_code(slice9_client)
    follow_res = slice9_client.post(
        f"/api/codes/{code}/follow",
        json={"channel": "discord", "discord_user_id": "777", "discord_username": "Tester"},
    )
    follow_id = follow_res.json()["follow_id"]

    c = TestClient(app, raise_server_exceptions=True)
    c.cookies.set("wp_listener_discord_id", "777")
    app.dependency_overrides  # overrides still active from slice9_client fixture
    res = c.delete(f"/api/follows/{follow_id}")
    assert res.status_code == 204


def test_list_follows_requires_auth():
    c = TestClient(app)
    res = c.get("/api/follows")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Notification service — SMS raises NotImplementedError
# ---------------------------------------------------------------------------

def test_sms_raises_not_implemented():
    import asyncio
    from app.repositories.follow_repository import SeedFollowRepository
    notif = NotificationService(SeedFollowRepository())
    with pytest.raises(NotImplementedError, match="SMS delivery is not enabled"):
        asyncio.run(notif._send_sms("+15005550006", "test"))


# ---------------------------------------------------------------------------
# Code generation — collision retry
# ---------------------------------------------------------------------------

def test_collision_retry_generates_unique_code(repos):
    """If first candidate already exists (active), second attempt succeeds."""
    import asyncio
    import app.services.code_service as code_svc_module

    code_repo, follow_repo, channel_repo = repos

    fixed_code = "FIXED1"
    existing = CodeDocument(
        code=fixed_code,
        channel_slug="late-night-house",
        entity_type="channel",
        entity_id="ch1",
        created_at=datetime.now(tz=timezone.utc),
        active=True,
    )
    asyncio.run(code_repo.create(existing))

    call_count = {"n": 0}
    original_random = code_svc_module._random_code

    def patched_random():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return fixed_code  # collision
        return original_random()

    code_svc_module._random_code = patched_random
    try:
        svc = CodeService(code_repo, channel_repo)
        from app.schemas.code import CodeCreateRequest
        req = CodeCreateRequest(channel_slug="late-night-house", entity_type="channel", entity_id="ch1")
        result = asyncio.run(svc.generate_code(req))
        assert result.code != fixed_code
        assert call_count["n"] >= 2
    finally:
        code_svc_module._random_code = original_random
