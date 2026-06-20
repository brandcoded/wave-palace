"""Tests for Slice 6 Sponsor Primitive: schema, admin PATCH, public events, mux overlay."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_channel_service
from app.api.routes import admin_auth as auth_routes
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.schemas.sponsor import Sponsor, sponsor_is_live
from app.services.channel_service import ChannelService
from app.services.mux_service import _drawtext_overlay

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SECRET = "test-secret-xyzzy-very-long-for-hmac-minimum"


def _auth_cookie() -> str:
    from app.core.auth import create_token
    return create_token()


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
    c.cookies.set("wp_admin_token", _auth_cookie())
    yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(repo) -> TestClient:
    svc = ChannelService(repo)
    app.dependency_overrides[get_channel_service] = lambda: svc
    c = TestClient(app, raise_server_exceptions=True)
    yield c
    app.dependency_overrides.clear()


_SLUG = "late-night-house"

_SPONSOR = {
    "name": "RedBull",
    "logoUrl": None,
    "text": "Brought to you by RedBull",
    "clickUrl": "https://redbull.com",
    "placement": "lower_third",
    "startDate": None,
    "endDate": None,
    "isActive": True,
    "isFeatured": False,
    "impressionCount": 0,
    "clickCount": 0,
}


# ---------------------------------------------------------------------------
# sponsor_is_live unit tests
# ---------------------------------------------------------------------------

def test_sponsor_is_live_active():
    sp = Sponsor(name="X", isActive=True)
    assert sponsor_is_live(sp)


def test_sponsor_is_live_inactive():
    sp = Sponsor(name="X", isActive=False)
    assert not sponsor_is_live(sp)


def test_sponsor_is_live_none():
    assert not sponsor_is_live(None)


def test_sponsor_is_live_before_start():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    sp = Sponsor(name="X", isActive=True, startDate=future)
    assert not sponsor_is_live(sp)


def test_sponsor_is_live_after_end():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    sp = Sponsor(name="X", isActive=True, endDate=past)
    assert not sponsor_is_live(sp)


def test_sponsor_is_live_within_window():
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    sp = Sponsor(name="X", isActive=True, startDate=start, endDate=end)
    assert sponsor_is_live(sp)


# ---------------------------------------------------------------------------
# Admin PATCH /api/admin/channels/{slug}/sponsor
# ---------------------------------------------------------------------------

def test_set_sponsor(client):
    r = client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    assert r.status_code == 200
    body = r.json()
    assert body["sponsor"]["name"] == "RedBull"
    assert body["sponsor"]["isActive"] is True


def test_update_sponsor(client):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    r = client.patch(
        f"/api/admin/channels/{_SLUG}/sponsor",
        json={**_SPONSOR, "text": "Powered by RedBull"},
    )
    assert r.status_code == 200
    assert r.json()["sponsor"]["text"] == "Powered by RedBull"


def test_clear_sponsor(client):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    r = client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=None)
    assert r.status_code == 200
    assert r.json()["sponsor"] is None


def test_set_sponsor_requires_auth(anon_client):
    r = anon_client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    assert r.status_code == 401


def test_set_sponsor_404(client):
    r = client.patch("/api/admin/channels/does-not-exist/sponsor", json=_SPONSOR)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/channels/{slug}/sponsor/impression
# ---------------------------------------------------------------------------

def test_impression_increments_when_live(client, anon_client, repo):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    r = anon_client.post(f"/api/channels/{_SLUG}/sponsor/impression")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["impressionCount"] == 1


def test_impression_noop_when_no_sponsor(anon_client, repo):
    r = anon_client.post(f"/api/channels/{_SLUG}/sponsor/impression")
    assert r.status_code == 200
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch.get("sponsor") is None


def test_impression_noop_when_inactive(client, anon_client, repo):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json={**_SPONSOR, "isActive": False})
    anon_client.post(f"/api/channels/{_SLUG}/sponsor/impression")
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["impressionCount"] == 0


def test_impression_noop_when_outside_window(client, anon_client, repo):
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    client.patch(
        f"/api/admin/channels/{_SLUG}/sponsor",
        json={**_SPONSOR, "endDate": past},
    )
    anon_client.post(f"/api/channels/{_SLUG}/sponsor/impression")
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["impressionCount"] == 0


# ---------------------------------------------------------------------------
# POST /api/channels/{slug}/sponsor/click
# ---------------------------------------------------------------------------

def test_click_increments_when_live(client, anon_client, repo):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    r = anon_client.post(f"/api/channels/{_SLUG}/sponsor/click")
    assert r.status_code == 200
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["clickCount"] == 1


def test_click_noop_when_no_sponsor(anon_client, repo):
    r = anon_client.post(f"/api/channels/{_SLUG}/sponsor/click")
    assert r.status_code == 200
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch.get("sponsor") is None


def test_click_noop_when_inactive(client, anon_client, repo):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json={**_SPONSOR, "isActive": False})
    anon_client.post(f"/api/channels/{_SLUG}/sponsor/click")
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["clickCount"] == 0


def test_multiple_clicks_each_increment(client, anon_client, repo):
    client.patch(f"/api/admin/channels/{_SLUG}/sponsor", json=_SPONSOR)
    anon_client.post(f"/api/channels/{_SLUG}/sponsor/click")
    anon_client.post(f"/api/channels/{_SLUG}/sponsor/click")
    ch = next(c for c in repo._channels if c["slug"] == _SLUG)
    assert ch["sponsor"]["clickCount"] == 2


# ---------------------------------------------------------------------------
# Mux _drawtext_overlay sponsor text
# ---------------------------------------------------------------------------

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@pytest.mark.skipif(not os.path.exists(_FONT), reason="font not available in CI")
def test_drawtext_includes_sponsor_text():
    overlay = _drawtext_overlay(
        title="Late Night House",
        host_name="DJ Test",
        genre="House",
        mood="Chill",
        font_path=_FONT,
        sponsor_text="Brought to you by RedBull",
    )
    assert "RedBull" in overlay


@pytest.mark.skipif(not os.path.exists(_FONT), reason="font not available in CI")
def test_drawtext_omits_sponsor_when_empty():
    overlay = _drawtext_overlay(
        title="Late Night House",
        host_name="DJ Test",
        genre="House",
        mood="Chill",
        font_path=_FONT,
        sponsor_text="",
    )
    assert "Brought to you by" not in overlay
    assert "sponsor" not in overlay.lower()


def test_drawtext_no_font_returns_empty():
    overlay = _drawtext_overlay(
        title="T",
        host_name="H",
        genre="G",
        mood="M",
        font_path="/nonexistent/font.ttf",
        sponsor_text="X",
    )
    assert overlay == ""
