"""Tests for Slice 7 — Production Analytics Dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analytics_service
from app.api.routes import admin_auth as auth_routes
from app.core.auth import create_token
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.code_repository import SeedCodeRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.schemas.code import CodeDocument
from app.schemas.follow import FollowDocument
from app.services.analytics_service import AnalyticsService

_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-long!"
_SECRET = "test-secret-xyzzy-very-long-for-hmac-minimum"

_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _patch_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", _SECRET)
    monkeypatch.setenv("JWT_SECRET", _JWT_SECRET)
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


def _admin_cookie() -> str:
    return create_token()


def _make_follow(
    id: str,
    channel_slug: str,
    notification_channel: str,
    confirmed: bool = True,
) -> FollowDocument:
    return FollowDocument(
        id=id,
        entity_type="channel",
        entity_id=channel_slug,
        channel_slug=channel_slug,
        notification_channel=notification_channel,
        confirmed=confirmed,
        created_at=_NOW,
        code_used="TESTCO",
    )


def _make_code(code: str, channel_slug: str, active: bool = True) -> CodeDocument:
    return CodeDocument(
        code=code,
        entity_type="channel",
        entity_id=channel_slug,
        channel_slug=channel_slug,
        active=active,
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_service():
    """Two published channels + one unpublished, follows, codes."""
    ch_repo = SeedChannelRepository()
    follow_repo = SeedFollowRepository()
    code_repo = SeedCodeRepository()

    # Inject channels directly into seed repo storage
    ch_repo._channels = [
        {
            "id": "ch1",
            "slug": "late-night-house",
            "title": "Late Night House",
            "hostName": "DJ Nova",
            "genre": ["house"],
            "mood": [],
            "isPublished": True,
            "playCount": 500,
            "streamingActive": False,
            "sponsor": {"isActive": True, "name": "Acme Co"},
            "muxLastAt": None,
        },
        {
            "id": "ch2",
            "slug": "daydream-drift",
            "title": "Daydream Drift",
            "hostName": "Solaris",
            "genre": ["ambient"],
            "mood": [],
            "isPublished": True,
            "playCount": 200,
            "streamingActive": True,
            "sponsor": None,
            "muxLastAt": None,
        },
        {
            "id": "ch3",
            "slug": "unpublished-channel",
            "title": "Draft Channel",
            "hostName": "Nobody",
            "genre": [],
            "mood": [],
            "isPublished": False,
            "playCount": 0,
            "streamingActive": False,
            "sponsor": None,
            "muxLastAt": None,
        },
    ]

    # Follows for ch1: 3 discord (2 confirmed, 1 not), 1 email confirmed
    follow_repo._follows = [
        _make_follow("f1", "late-night-house", "discord", confirmed=True),
        _make_follow("f2", "late-night-house", "discord", confirmed=True),
        _make_follow("f3", "late-night-house", "discord", confirmed=False),  # unconfirmed — excluded
        _make_follow("f4", "late-night-house", "email", confirmed=True),
        _make_follow("f5", "daydream-drift", "browser_push", confirmed=True),
    ]

    # Codes: 2 active for ch1, 1 inactive, 1 active for ch2
    code_repo._codes = [
        _make_code("LNHOU1", "late-night-house", active=True),
        _make_code("LNHOU2", "late-night-house", active=True),
        _make_code("LNHOU3", "late-night-house", active=False),
        _make_code("DDRIT1", "daydream-drift", active=True),
    ]

    return AnalyticsService(ch_repo, follow_repo, code_repo)


@pytest.fixture()
def analytics_client(seeded_service):
    app.dependency_overrides[get_analytics_service] = lambda: seeded_service
    with TestClient(app) as c:
        c.cookies.set("wp_admin_token", _admin_cookie())
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(seeded_service):
    app.dependency_overrides[get_analytics_service] = lambda: seeded_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

def test_unauthenticated_returns_401(anon_client):
    res = anon_client.get("/api/admin/analytics")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Shape / 200
# ---------------------------------------------------------------------------

def test_returns_200(analytics_client):
    res = analytics_client.get("/api/admin/analytics")
    assert res.status_code == 200


def test_response_has_required_keys(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    for key in (
        "total_plays", "total_follows", "total_channels",
        "published_channels", "channels_with_sponsor",
        "follow_breakdown", "top_channels", "generated_at",
    ):
        assert key in data, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Aggregate totals
# ---------------------------------------------------------------------------

def test_total_plays_is_sum_of_all_channels(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    assert data["total_plays"] == 700  # 500 + 200 + 0


def test_total_follows_counts_confirmed_only(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    # f1, f2 (discord), f4 (email), f5 (browser_push) = 4; f3 is unconfirmed
    assert data["total_follows"] == 4


def test_total_channels(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    assert data["total_channels"] == 3


def test_published_channels(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    assert data["published_channels"] == 2


def test_channels_with_sponsor(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    assert data["channels_with_sponsor"] == 1


# ---------------------------------------------------------------------------
# Follow breakdown
# ---------------------------------------------------------------------------

def test_follow_breakdown_totals(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    bd = data["follow_breakdown"]
    assert bd["discord"] == 2
    assert bd["email"] == 1
    assert bd["browser_push"] == 1


def test_follow_breakdown_matches_per_channel_sum(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    global_bd = data["follow_breakdown"]
    per_channel_discord = sum(
        ch["follow_breakdown"]["discord"] for ch in data["top_channels"]
    )
    assert per_channel_discord == global_bd["discord"]


# ---------------------------------------------------------------------------
# Leaderboard ordering
# ---------------------------------------------------------------------------

def test_top_channels_sorted_by_play_count_descending(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    plays = [ch["play_count"] for ch in data["top_channels"]]
    assert plays == sorted(plays, reverse=True)


def test_all_channels_included_in_leaderboard(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    assert len(data["top_channels"]) == 3


# ---------------------------------------------------------------------------
# Per-channel stats
# ---------------------------------------------------------------------------

def test_channel_stat_fields(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    ch = next(c for c in data["top_channels"] if c["slug"] == "late-night-house")
    assert ch["play_count"] == 500
    assert ch["follow_count"] == 3   # f1, f2, f4 (confirmed)
    assert ch["active_code_count"] == 2
    assert ch["is_published"] is True
    assert ch["follow_breakdown"]["discord"] == 2
    assert ch["follow_breakdown"]["email"] == 1
    assert ch["follow_breakdown"]["browser_push"] == 0


def test_no_pii_in_response(analytics_client):
    data = analytics_client.get("/api/admin/analytics").json()
    raw = str(data)
    assert "example.com" not in raw
    assert "discord_user_id" not in raw
