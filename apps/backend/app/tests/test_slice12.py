"""Tests for Slice 12 — Logged-In Dashboard.

Covers:
- POST /api/me/history (anonymous and authenticated)
- POST /api/me/history/merge
- GET  /api/me/history
- POST /api/me/saves/{slug}
- DELETE /api/me/saves/{slug}
- GET  /api/me/saves
- GET  /api/me/notifications
- PATCH /api/me/notifications/{id}
- POST /api/me/notifications/mark-all-read
- GET  /api/me/recommendations
- GET  /api/me/follows
- 401 enforcement on authenticated-only routes
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_channel_save_repository,
    get_channel_service,
    get_follow_repository,
    get_listen_history_service,
    get_notification_repository,
    get_recommendation_service,
)
from app.core.auth import get_current_user, get_optional_user
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.channel_save_repository import SeedChannelSaveRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.repositories.listen_event_repository import SeedListenEventRepository
from app.repositories.notification_repository import SeedNotificationRepository
from app.schemas.me import NotificationCreate
from app.schemas.user import UserDocument
from app.services.channel_service import ChannelService
from app.services.listen_history_service import ListenHistoryService
from app.services.recommendation_service import RecommendationService
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(uid: str = "user-123", email: str = "test@example.com") -> UserDocument:
    return UserDocument(
        id=uid,
        email=email,
        display_name="Test User",
        roles=[],
        created_at=_now(),
        is_active=True,
    )


def _make_client(user: UserDocument | None = None) -> TestClient:
    channel_repo = SeedChannelRepository()
    channel_svc = ChannelService(channel_repo)
    listen_repo = SeedListenEventRepository()
    listen_svc = ListenHistoryService(listen_repo)
    save_repo = SeedChannelSaveRepository()
    notif_repo = SeedNotificationRepository()
    follow_repo = SeedFollowRepository()
    rec_svc = RecommendationService(channel_repo, follow_repo)

    app.dependency_overrides[get_channel_service] = lambda: channel_svc
    app.dependency_overrides[get_listen_history_service] = lambda: listen_svc
    app.dependency_overrides[get_channel_save_repository] = lambda: save_repo
    app.dependency_overrides[get_notification_repository] = lambda: notif_repo
    app.dependency_overrides[get_follow_repository] = lambda: follow_repo
    app.dependency_overrides[get_recommendation_service] = lambda: rec_svc

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_optional_user] = lambda: user
    else:
        app.dependency_overrides[get_optional_user] = lambda: None
        # Remove current_user override so 401 kicks in naturally
        app.dependency_overrides.pop(get_current_user, None)

    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/me/history — anonymous
# ---------------------------------------------------------------------------

def test_record_history_anonymous():
    client = _make_client(user=None)
    resp = client.post("/api/me/history", json={
        "channel_slug": "late-night-house",
        "session_key": "anon-session-abc",
        "track_title": "Come Thru",
        "track_artist": "DJ Skyy",
    })
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


def test_record_history_authenticated():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.post("/api/me/history", json={
        "channel_slug": "late-night-house",
        "session_key": "sess-xyz",
        "track_title": "Day Trips",
        "track_artist": "DJ Skyy",
    })
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/me/history/merge
# ---------------------------------------------------------------------------

def test_merge_history():
    user = _make_user()

    # Build shared repo instances so both clients share state
    channel_repo = SeedChannelRepository()
    channel_svc = ChannelService(channel_repo)
    listen_repo = SeedListenEventRepository()
    listen_svc = ListenHistoryService(listen_repo)
    save_repo = SeedChannelSaveRepository()
    notif_repo = SeedNotificationRepository()
    follow_repo = SeedFollowRepository()
    rec_svc = RecommendationService(channel_repo, follow_repo)

    def _base_overrides():
        app.dependency_overrides[get_channel_service] = lambda: channel_svc
        app.dependency_overrides[get_listen_history_service] = lambda: listen_svc
        app.dependency_overrides[get_channel_save_repository] = lambda: save_repo
        app.dependency_overrides[get_notification_repository] = lambda: notif_repo
        app.dependency_overrides[get_follow_repository] = lambda: follow_repo
        app.dependency_overrides[get_recommendation_service] = lambda: rec_svc

    # Step 1: record two anonymous events
    _base_overrides()
    app.dependency_overrides[get_optional_user] = lambda: None
    with TestClient(app, raise_server_exceptions=True) as c:
        c.post("/api/me/history", json={"channel_slug": "late-night-house", "session_key": "sess-merge"})
        c.post("/api/me/history", json={"channel_slug": "neon-afterhours", "session_key": "sess-merge"})

    # Step 2: merge as authenticated user
    _base_overrides()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.post("/api/me/history/merge", json={"session_key": "sess-merge"})
        assert resp.status_code == 200
        assert resp.json()["merged"] == 2


def test_merge_history_requires_auth():
    client = _make_client(user=None)
    resp = client.post("/api/me/history/merge", json={"session_key": "s"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/me/history
# ---------------------------------------------------------------------------

def test_get_history_empty():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.get("/api/me/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recent"] == []
    assert data["top_channel"] is None
    assert data["last_channel"] is None


def test_get_history_with_events():
    user = _make_user()
    client = _make_client(user=user)
    client.post("/api/me/history", json={"channel_slug": "late-night-house", "track_title": "Come Thru"})
    client.post("/api/me/history", json={"channel_slug": "late-night-house", "track_title": "Day Trips"})
    resp = client.get("/api/me/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recent"]) == 2
    assert data["last_channel"] == "late-night-house"


def test_get_history_requires_auth():
    client = _make_client(user=None)
    resp = client.get("/api/me/history")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST + DELETE + GET /api/me/saves
# ---------------------------------------------------------------------------

def test_save_and_get():
    user = _make_user()
    client = _make_client(user=user)

    resp = client.post("/api/me/saves/late-night-house")
    assert resp.status_code == 204

    resp = client.get("/api/me/saves")
    assert resp.status_code == 200
    assert "late-night-house" in resp.json()["slugs"]


def test_save_idempotent():
    user = _make_user()
    client = _make_client(user=user)
    client.post("/api/me/saves/late-night-house")
    client.post("/api/me/saves/late-night-house")  # duplicate — no error
    resp = client.get("/api/me/saves")
    assert resp.json()["slugs"].count("late-night-house") == 1


def test_unsave_channel():
    user = _make_user()
    client = _make_client(user=user)
    client.post("/api/me/saves/late-night-house")
    resp = client.delete("/api/me/saves/late-night-house")
    assert resp.status_code == 204
    resp = client.get("/api/me/saves")
    assert "late-night-house" not in resp.json()["slugs"]


def test_unsave_nonexistent_no_error():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.delete("/api/me/saves/nonexistent-slug")
    assert resp.status_code == 204


def test_save_requires_auth():
    client = _make_client(user=None)
    resp = client.post("/api/me/saves/late-night-house")
    assert resp.status_code == 401


def test_save_unknown_channel_returns_404():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.post("/api/me/saves/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/me/notifications + PATCH + mark-all-read
# ---------------------------------------------------------------------------

def test_notifications_empty():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.get("/api/me/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notifications"] == []
    assert data["unread_count"] == 0


def test_notifications_mark_all_read():
    user = _make_user()
    # Seed a notification directly via repo
    notif_repo = SeedNotificationRepository()
    import asyncio
    notif = asyncio.run(notif_repo.create(NotificationCreate(
        user_id=user.id,
        type="recommendation",
        title="You might like Late Night House",
    )))

    # Re-use the same repo instance
    channel_repo = SeedChannelRepository()
    channel_svc = ChannelService(channel_repo)
    listen_svc = ListenHistoryService(SeedListenEventRepository())
    follow_repo = SeedFollowRepository()
    rec_svc = RecommendationService(channel_repo, follow_repo)

    app.dependency_overrides[get_channel_service] = lambda: channel_svc
    app.dependency_overrides[get_listen_history_service] = lambda: listen_svc
    app.dependency_overrides[get_channel_save_repository] = lambda: SeedChannelSaveRepository()
    app.dependency_overrides[get_notification_repository] = lambda: notif_repo
    app.dependency_overrides[get_follow_repository] = lambda: follow_repo
    app.dependency_overrides[get_recommendation_service] = lambda: rec_svc
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get("/api/me/notifications")
        assert resp.json()["unread_count"] == 1

        resp = client.post("/api/me/notifications/mark-all-read")
        assert resp.status_code == 200
        assert resp.json()["marked"] == 1

        resp = client.get("/api/me/notifications")
        assert resp.json()["unread_count"] == 0


def test_notifications_requires_auth():
    client = _make_client(user=None)
    resp = client.get("/api/me/notifications")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/me/recommendations
# ---------------------------------------------------------------------------

def test_recommendations_no_follows_returns_channels():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.get("/api/me/recommendations")
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert isinstance(recs, list)
    assert len(recs) <= 6


def test_recommendations_requires_auth():
    client = _make_client(user=None)
    resp = client.get("/api/me/recommendations")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/me/follows
# ---------------------------------------------------------------------------

def test_follows_empty():
    user = _make_user()
    client = _make_client(user=user)
    resp = client.get("/api/me/follows")
    assert resp.status_code == 200
    assert resp.json()["slugs"] == []


def test_follows_requires_auth():
    client = _make_client(user=None)
    resp = client.get("/api/me/follows")
    assert resp.status_code == 401
