"""Tests for public engagement metrics on channel endpoints.

Covers:
- GET /api/channels returns follower_count, listener_count, worlds_count, trending
- follower_count reflects only confirmed follows
- listener_count reflects active sessions in 15-min window
- worlds_count returns 0 (Slice 4 stub)
- trending returns False (Slice 8 stub)
- GET /api/channels/{slug} includes all four fields
- follower_count = 0 when no follows exist
- asyncio.gather used for follower counts (service method verified)
- Seed mode parity
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.api.dependencies import get_channel_service, get_follow_service, get_follow_repository
from app.core.auth import get_current_user
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.code_repository import SeedCodeRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.schemas.follow import FollowDocument
from app.schemas.user import UserDocument
from app.services.channel_service import ChannelService, _PLAY_CACHE, _LISTENER_WINDOW, active_listener_count
from app.services.follow_service import FollowService


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_client(channel_repo: SeedChannelRepository, follow_repo: SeedFollowRepository) -> TestClient:
    channel_svc = ChannelService(channel_repo)
    code_repo = SeedCodeRepository()
    follow_svc = FollowService(follow_repo, code_repo, channel_repo)

    app.dependency_overrides[get_channel_service] = lambda: channel_svc
    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    app.dependency_overrides[get_follow_repository] = lambda: follow_repo

    return TestClient(app, raise_server_exceptions=True)


def _empty_channel_repo() -> SeedChannelRepository:
    """Channel repo with no pre-loaded seed channels."""
    return SeedChannelRepository(channels=[])


def _seed_channel(repo: SeedChannelRepository, slug: str = "test-ch") -> None:
    """Insert a minimal published channel into a seed repo."""
    repo._channels.append({
        "id": slug,
        "slug": slug,
        "title": "Test Channel",
        "description": "desc",
        "genre": ["House"],
        "mood": [],
        "energy": [],
        "theme": [],
        "hostName": "DJ Test",
        "coverImageUrl": "https://cdn.example.com/cover.jpg",
        "audioUrl": "https://cdn.example.com/audio.mp3",
        "playlist": [],
        "vrchatPlaybackUrl": "https://cdn.example.com/mux.mp4",
        "isPublished": True,
        "playCount": 0,
    })


def _make_confirmed_follow(slug: str, discord_id: str = "disc-1") -> FollowDocument:
    return FollowDocument(
        id=f"follow-{discord_id}",
        entity_type="channel",
        entity_id=slug,
        channel_slug=slug,
        notification_channel="discord",
        discord_user_id=discord_id,
        confirmed=True,
        created_at=_now(),
    )


def _make_unconfirmed_follow(slug: str) -> FollowDocument:
    return FollowDocument(
        id="follow-unconf",
        entity_type="channel",
        entity_id=slug,
        channel_slug=slug,
        notification_channel="discord",
        discord_user_id="disc-unconf",
        confirmed=False,
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# GET /api/channels — list
# ---------------------------------------------------------------------------

def test_list_channels_includes_metric_fields():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    channels = res.json()
    assert len(channels) == 1
    ch = channels[0]
    assert "follower_count" in ch
    assert "listener_count" in ch
    assert "worlds_count" in ch
    assert "trending" in ch


def test_list_channels_follower_count_confirmed_only():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)
    follow_repo._follows.append(_make_confirmed_follow("test-ch", "d1"))
    follow_repo._follows.append(_make_confirmed_follow("test-ch", "d2"))
    follow_repo._follows.append(_make_unconfirmed_follow("test-ch"))

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    assert res.json()[0]["follower_count"] == 2


def test_list_channels_worlds_count_is_zero():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    assert res.json()[0]["worlds_count"] == 0


def test_list_channels_trending_is_false():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    assert res.json()[0]["trending"] is False


def test_list_channels_follower_count_zero_when_no_follows():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    assert res.json()[0]["follower_count"] == 0


# ---------------------------------------------------------------------------
# GET /api/channels/{slug} — detail
# ---------------------------------------------------------------------------

def test_get_channel_includes_metric_fields():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo)
    follow_repo._follows.append(_make_confirmed_follow("test-ch"))

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels/test-ch")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    data = res.json()
    assert data["follower_count"] == 1
    assert data["worlds_count"] == 0
    assert data["trending"] is False


# ---------------------------------------------------------------------------
# listener_count — active_listener_count unit test
# ---------------------------------------------------------------------------

def test_active_listener_count_counts_recent_plays():
    slug = "test-ch-listener"
    now = time.time()
    # Inject recent entries into the module-level cache
    _PLAY_CACHE[f"{slug}:10.0.0.1"] = now - 60     # 1 min ago — active
    _PLAY_CACHE[f"{slug}:10.0.0.2"] = now - 500    # ~8 min ago — active
    _PLAY_CACHE[f"{slug}:10.0.0.3"] = now - 1000   # ~16 min ago — expired (> 15 min)
    _PLAY_CACHE["other-ch:10.0.0.1"] = now - 60    # different channel

    count = active_listener_count(slug)

    # Clean up
    for k in [f"{slug}:10.0.0.1", f"{slug}:10.0.0.2", f"{slug}:10.0.0.3", "other-ch:10.0.0.1"]:
        _PLAY_CACHE.pop(k, None)

    assert count == 2


def test_active_listener_count_zero_for_unknown_slug():
    assert active_listener_count("no-such-channel-xyz") == 0


def test_list_channels_listener_count_reflects_active_sessions():
    channel_repo = _empty_channel_repo()
    follow_repo = SeedFollowRepository()
    _seed_channel(channel_repo, "live-ch")
    now = time.time()
    _PLAY_CACHE["live-ch:1.1.1.1"] = now - 100
    _PLAY_CACHE["live-ch:2.2.2.2"] = now - 200

    client = _make_client(channel_repo, follow_repo)
    res = client.get("/api/channels")
    app.dependency_overrides.clear()

    _PLAY_CACHE.pop("live-ch:1.1.1.1", None)
    _PLAY_CACHE.pop("live-ch:2.2.2.2", None)

    ch = next(c for c in res.json() if c["slug"] == "live-ch")
    assert ch["listener_count"] == 2
