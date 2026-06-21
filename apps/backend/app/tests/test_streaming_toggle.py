"""Tests for Pre-Slice 4 add-on: streaming readiness + mux/stream toggle."""

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


@pytest.fixture(autouse=True)
def _patch_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", _SECRET)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long!")
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


@pytest.fixture()
def streaming_client():
    repo = SeedChannelRepository()
    svc = ChannelService(repo)
    app.dependency_overrides[get_channel_service] = lambda: svc
    c = TestClient(app)
    c.cookies.set("wp_admin_token", create_token())
    yield c
    app.dependency_overrides.clear()


def test_streaming_active_defaults_to_false(streaming_client):
    res = streaming_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert not res.json().get("streamingActive", False)


def test_patch_streaming_active_true(streaming_client):
    res = streaming_client.patch(
        "/api/admin/channels/late-night-house",
        json={"streamingActive": True, "vrchatFallbackUrl": "https://stream.example.com/live.m3u8"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["streamingActive"] is True
    assert data["vrchatFallbackUrl"] == "https://stream.example.com/live.m3u8"


def test_patch_streaming_active_false(streaming_client):
    streaming_client.patch("/api/admin/channels/late-night-house", json={"streamingActive": True})
    res = streaming_client.patch("/api/admin/channels/late-night-house", json={"streamingActive": False})
    assert res.status_code == 200
    assert res.json()["streamingActive"] is False


def test_streaming_does_not_set_mux_outdated(streaming_client):
    res = streaming_client.patch(
        "/api/admin/channels/late-night-house",
        json={"streamingActive": True},
    )
    assert res.status_code == 200
    assert not res.json().get("muxOutdated", False)


def test_bulk_streaming_activate(streaming_client):
    res = streaming_client.post(
        "/api/admin/channels/streaming/bulk",
        json={"streamingActive": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["updated"] >= 1
    assert data["streamingActive"] is True


def test_bulk_streaming_deactivate(streaming_client):
    streaming_client.post("/api/admin/channels/streaming/bulk", json={"streamingActive": True})
    res = streaming_client.post(
        "/api/admin/channels/streaming/bulk",
        json={"streamingActive": False},
    )
    assert res.status_code == 200
    assert res.json()["streamingActive"] is False


def test_public_api_exposes_streaming_fields(streaming_client):
    res = streaming_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    data = res.json()
    assert "streamingActive" in data
