def test_list_returns_published_channels(client):
    res = client.get("/api/channels")
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) == 3
    assert all(c["isPublished"] for c in channels)


def test_list_excludes_unpublished_channels(client):
    res = client.get("/api/channels")
    slugs = {c["slug"] for c in res.json()}
    assert "hidden-draft" not in slugs


def test_get_channel_by_slug(client):
    res = client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json()["title"] == "Late Night House"


def test_missing_channel_returns_404(client):
    res = client.get("/api/channels/does-not-exist")
    assert res.status_code == 404


def test_unpublished_channel_by_slug_returns_404(client):
    res = client.get("/api/channels/hidden-draft")
    assert res.status_code == 404


def test_filter_by_genre(client):
    res = client.get("/api/channels", params={"genre": "House"})
    channels = res.json()
    assert len(channels) == 1
    assert channels[0]["slug"] == "late-night-house"


def test_filter_by_mood(client):
    res = client.get("/api/channels", params={"mood": "Dark"})
    channels = res.json()
    assert len(channels) == 1
    assert channels[0]["slug"] == "neon-afterhours"


def test_filter_is_case_insensitive(client):
    res = client.get("/api/channels", params={"genre": "house"})
    assert len(res.json()) == 1


def test_filter_combination_returns_empty(client):
    res = client.get("/api/channels", params={"genre": "House", "mood": "Dark"})
    assert res.json() == []


# ---------------------------------------------------------------------------
# Sponsor visibility on public API (Slice 6)
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone

import pytest
from app.api.dependencies import get_channel_service
from app.api.routes import admin_auth as auth_routes
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.services.channel_service import ChannelService
from app.core.auth import create_token

_SPONSOR_BASE = {
    "name": "Neon Co",
    "logoUrl": None,
    "text": "Brought to you by Neon",
    "clickUrl": "https://neon.example.com",
    "placement": "lower_third",
    "startDate": None,
    "endDate": None,
    "isActive": True,
    "isFeatured": False,
    "impressionCount": 0,
    "clickCount": 0,
}


@pytest.fixture()
def sponsor_repo():
    return SeedChannelRepository()


@pytest.fixture(autouse=False)
def _patch_secrets_channels(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "test-secret-xyzzy-very-long-for-hmac-minimum")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long!")
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


@pytest.fixture()
def sponsor_client(sponsor_repo, _patch_secrets_channels):
    svc = ChannelService(sponsor_repo)
    app.dependency_overrides[get_channel_service] = lambda: svc
    from fastapi.testclient import TestClient
    c = TestClient(app)
    c.cookies.set("wp_admin_token", create_token())
    yield c
    app.dependency_overrides.clear()


def test_active_sponsor_included_in_public_response(sponsor_client):
    """Active sponsor within no date window is exposed on the public channel API."""
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=_SPONSOR_BASE)
    res = sponsor_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    sp = res.json().get("sponsor")
    assert sp is not None
    assert sp["name"] == "Neon Co"


def test_inactive_sponsor_stripped_from_public_response(sponsor_client):
    """Inactive sponsor is not exposed on the public channel API."""
    payload = {**_SPONSOR_BASE, "isActive": False}
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=payload)
    res = sponsor_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json().get("sponsor") is None


def test_sponsor_before_start_date_stripped(sponsor_client):
    """Sponsor with a future startDate is not exposed on the public channel API."""
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {**_SPONSOR_BASE, "startDate": future}
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=payload)
    res = sponsor_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json().get("sponsor") is None


def test_sponsor_after_end_date_stripped(sponsor_client):
    """Sponsor with a past endDate is not exposed on the public channel API."""
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    payload = {**_SPONSOR_BASE, "endDate": past}
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=payload)
    res = sponsor_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json().get("sponsor") is None


def test_sponsor_within_active_window_included(sponsor_client):
    """Sponsor within startDate..endDate is exposed on the public channel API."""
    start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {**_SPONSOR_BASE, "startDate": start, "endDate": end}
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=payload)
    res = sponsor_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert res.json().get("sponsor") is not None


def test_active_sponsor_included_in_channel_list(sponsor_client):
    """Active sponsor is also exposed on the public channel list endpoint."""
    sponsor_client.patch("/api/admin/channels/late-night-house/sponsor", json=_SPONSOR_BASE)
    channels = sponsor_client.get("/api/channels").json()
    target = next((c for c in channels if c["slug"] == "late-night-house"), None)
    assert target is not None
    assert target.get("sponsor") is not None
