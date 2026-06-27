"""Tests for follow-status and follower-count endpoints.

Covers:
- GET /api/me/follows/{slug}  → 200 following: true  (confirmed follow)
- GET /api/me/follows/{slug}  → 200 following: false (no follow)
- GET /api/me/follows/{slug}  → 200 following: false (unconfirmed follow)
- GET /api/me/follows/{slug}  → 401 when unauthenticated
- GET /api/channels/{slug}/followers/count → {count: N} for N confirmed
- GET /api/channels/{slug}/followers/count → {count: 0} when no follows
- GET /api/channels/{slug}/followers/count → {count: 0} excludes unconfirmed
- SeedFollowRepository.count_confirmed_by_channel returns correct value
- SeedFollowRepository.get_by_user_and_channel seed parity
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.api.dependencies import get_follow_repository, get_follow_service, get_channel_service
from app.core.auth import get_current_user
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.schemas.follow import FollowDocument
from app.schemas.user import UserDocument
from app.services.channel_service import ChannelService
from app.services.follow_service import FollowService
from app.repositories.code_repository import SeedCodeRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(uid: str = "user-1", discord_id: str | None = "disc-1", email: str | None = None) -> UserDocument:
    return UserDocument(
        id=uid,
        discord_user_id=discord_id,
        email=email,
        display_name="Test User",
        roles=[],
        created_at=_now(),
        is_active=True,
    )


def _make_follow(
    channel_slug: str = "test-channel",
    discord_user_id: str | None = "disc-1",
    email: str | None = None,
    confirmed: bool = True,
) -> FollowDocument:
    return FollowDocument(
        id="follow-abc",
        entity_type="channel",
        entity_id=channel_slug,
        channel_slug=channel_slug,
        notification_channel="discord",
        discord_user_id=discord_user_id,
        email=email,
        confirmed=confirmed,
        created_at=_now(),
    )


def _make_client(user: UserDocument | None, follow_repo: SeedFollowRepository) -> TestClient:
    channel_repo = SeedChannelRepository()
    code_repo = SeedCodeRepository()
    follow_svc = FollowService(follow_repo, code_repo, channel_repo)
    channel_svc = ChannelService(channel_repo)

    app.dependency_overrides[get_follow_repository] = lambda: follow_repo
    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    app.dependency_overrides[get_channel_service] = lambda: channel_svc

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user

    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# GET /api/me/follows/{slug}
# ---------------------------------------------------------------------------

def test_follow_status_confirmed_returns_following_true():
    repo = SeedFollowRepository()
    user = _make_user()
    follow = _make_follow(confirmed=True)
    repo._follows.append(follow)

    client = _make_client(user, repo)
    res = client.get("/api/me/follows/test-channel")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    data = res.json()
    assert data["following"] is True
    assert data["follow_id"] == "follow-abc"


def test_follow_status_no_follow_returns_false():
    repo = SeedFollowRepository()
    user = _make_user()

    client = _make_client(user, repo)
    res = client.get("/api/me/follows/test-channel")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    data = res.json()
    assert data["following"] is False
    assert data["follow_id"] is None


def test_follow_status_unconfirmed_returns_false():
    repo = SeedFollowRepository()
    user = _make_user()
    follow = _make_follow(confirmed=False)
    repo._follows.append(follow)

    client = _make_client(user, repo)
    res = client.get("/api/me/follows/test-channel")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    data = res.json()
    assert data["following"] is False


def test_follow_status_unauthenticated_returns_401():
    repo = SeedFollowRepository()
    # No user override — no dependency override for get_current_user
    channel_repo = SeedChannelRepository()
    code_repo = SeedCodeRepository()
    follow_svc = FollowService(repo, code_repo, channel_repo)
    app.dependency_overrides[get_follow_service] = lambda: follow_svc

    client = TestClient(app, raise_server_exceptions=True)
    res = client.get("/api/me/follows/test-channel")
    app.dependency_overrides.clear()

    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/channels/{slug}/followers/count
# ---------------------------------------------------------------------------

def test_follower_count_returns_confirmed_count():
    repo = SeedFollowRepository()
    # Two confirmed, one unconfirmed
    repo._follows.append(_make_follow(discord_user_id="d1", confirmed=True))
    repo._follows.append(_make_follow(discord_user_id="d2", confirmed=True))
    repo._follows.append(_make_follow(discord_user_id="d3", confirmed=False))

    client = _make_client(None, repo)
    res = client.get("/api/channels/test-channel/followers/count")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert res.json()["count"] == 2


def test_follower_count_zero_when_no_follows():
    repo = SeedFollowRepository()

    client = _make_client(None, repo)
    res = client.get("/api/channels/test-channel/followers/count")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert res.json()["count"] == 0


def test_follower_count_excludes_unconfirmed():
    repo = SeedFollowRepository()
    repo._follows.append(_make_follow(discord_user_id="d1", confirmed=False))
    repo._follows.append(_make_follow(discord_user_id="d2", confirmed=False))

    client = _make_client(None, repo)
    res = client.get("/api/channels/test-channel/followers/count")
    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert res.json()["count"] == 0


# ---------------------------------------------------------------------------
# Seed repository unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_count_confirmed_by_channel():
    repo = SeedFollowRepository()
    repo._follows.append(_make_follow(channel_slug="ch-a", discord_user_id="d1", confirmed=True))
    repo._follows.append(_make_follow(channel_slug="ch-a", discord_user_id="d2", confirmed=True))
    repo._follows.append(_make_follow(channel_slug="ch-a", discord_user_id="d3", confirmed=False))
    repo._follows.append(_make_follow(channel_slug="ch-b", discord_user_id="d4", confirmed=True))

    assert await repo.count_confirmed_by_channel("ch-a") == 2
    assert await repo.count_confirmed_by_channel("ch-b") == 1
    assert await repo.count_confirmed_by_channel("ch-c") == 0


@pytest.mark.asyncio
async def test_seed_get_by_user_and_channel_discord():
    repo = SeedFollowRepository()
    follow = _make_follow(channel_slug="my-channel", discord_user_id="disc-99", confirmed=True)
    repo._follows.append(follow)

    result = await repo.get_by_user_and_channel("disc-99", None, "my-channel")
    assert result is not None
    assert result.id == "follow-abc"

    # Different channel — no result
    result2 = await repo.get_by_user_and_channel("disc-99", None, "other-channel")
    assert result2 is None


@pytest.mark.asyncio
async def test_seed_get_by_user_and_channel_email():
    repo = SeedFollowRepository()
    follow = FollowDocument(
        id="follow-email",
        entity_type="channel",
        entity_id="my-channel",
        channel_slug="my-channel",
        notification_channel="email",
        email="test@example.com",
        confirmed=True,
        created_at=_now(),
    )
    repo._follows.append(follow)

    result = await repo.get_by_user_and_channel(None, "test@example.com", "my-channel")
    assert result is not None
    assert result.id == "follow-email"


@pytest.mark.asyncio
async def test_seed_get_by_user_and_channel_no_identity_returns_none():
    repo = SeedFollowRepository()
    repo._follows.append(_make_follow(confirmed=True))

    result = await repo.get_by_user_and_channel(None, None, "test-channel")
    assert result is None
