"""Tests for mux-outdated system: dirty flag, auto-set on overlay changes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_channel_service
from app.api.routes import admin_auth as auth_routes
from app.core.auth import create_token
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.services.channel_service import ChannelService


_SECRET = "test-secret-xyzzy-very-long-for-hmac-minimum"
_SLUG = "late-night-house"

_OVERLAY_FIELDS = {
    "title", "hostName", "genre", "mood",
    "visualLoopUrl", "coverImageUrl", "playlist",
}


@pytest.fixture(autouse=True)
def _patch_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", _SECRET)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long!")
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


@pytest.fixture()
def repo() -> SeedChannelRepository:
    return SeedChannelRepository()


@pytest.fixture()
def client(repo) -> TestClient:
    svc = ChannelService(repo)
    app.dependency_overrides[get_channel_service] = lambda: svc
    c = TestClient(app, raise_server_exceptions=True)
    c.cookies.set("wp_admin_token", create_token())
    yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# muxOutdated tests
# ---------------------------------------------------------------------------


def test_patch_overlay_field_sets_mux_outdated(client):
    """PATCH with an overlay-affecting field (title) sets muxOutdated: true."""
    res = client.patch(
        f"/api/admin/channels/{_SLUG}",
        json={"title": "New Title"},
    )
    assert res.status_code == 200
    assert res.json()["muxOutdated"] is True


def test_patch_non_overlay_field_does_not_set_mux_outdated(client):
    """PATCH with a non-overlay field (description) does NOT set muxOutdated."""
    res = client.patch(
        f"/api/admin/channels/{_SLUG}",
        json={"description": "New description"},
    )
    assert res.status_code == 200
    data = res.json()
    # muxOutdated should remain False (or not be set if it wasn't before)
    assert data.get("muxOutdated") is not True


def test_patch_multiple_fields_with_overlay_sets_mux_outdated(client):
    """PATCH with both overlay and non-overlay fields sets muxOutdated if any overlay field present."""
    res = client.patch(
        f"/api/admin/channels/{_SLUG}",
        json={"title": "New", "description": "New desc"},
    )
    assert res.status_code == 200
    assert res.json()["muxOutdated"] is True


def test_patch_sponsor_sets_mux_outdated(client):
    """PATCH /sponsor with a sponsor body sets muxOutdated: true."""
    sponsor = {
        "name": "Test Sponsor",
        "logoUrl": None,
        "text": "Brought to you by Test",
        "clickUrl": "https://test.com",
        "placement": "lower_third",
        "startDate": None,
        "endDate": None,
        "isActive": True,
        "isFeatured": False,
        "impressionCount": 0,
        "clickCount": 0,
    }
    res = client.patch(
        f"/api/admin/channels/{_SLUG}/sponsor",
        json=sponsor,
    )
    assert res.status_code == 200
    assert res.json()["muxOutdated"] is True


def test_patch_sponsor_clear_sets_mux_outdated(client):
    """PATCH /sponsor with null (clear) sets muxOutdated: true."""
    res = client.patch(
        f"/api/admin/channels/{_SLUG}/sponsor",
        json=None,
    )
    assert res.status_code == 200
    assert res.json()["muxOutdated"] is True
