"""Tests for Slice 13 — Notification System + one-click follow add-on.

Covers:
- FollowDocument notify_* defaults and backfill
- GET /api/follows returns notify_* fields
- PATCH /api/follows/{id} updates notify_* preferences
- notify_new_tracks delivery, throttle, filtering
- send_weekly_digest email grouping and throttle
- POST /api/admin/notifications/digest
- POST /api/admin/channels/{slug}/notify (admin manual trigger)
- PATCH /api/admin/channels/{slug} fires notification on new tracks
- POST /api/codes/{code}/follow/me (one-click follow for logged-in users)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_channel_service,
    get_code_service,
    get_follow_repository,
    get_follow_service,
    get_notification_delivery_service,
    get_notification_repository,
)
from app.core.auth import get_current_admin, get_current_user
from app.core.config import Settings
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.follow_repository import SeedFollowRepository
from app.repositories.notification_repository import SeedNotificationRepository
from app.repositories.throttle_repository import SeedThrottleRepository
from app.repositories.user_repository import SeedUserRepository
from app.schemas.follow import FollowDocument
from app.schemas.user import UserDocument
from app.services.channel_service import ChannelService
from app.services.listen_history_service import ListenHistoryService
from app.repositories.listen_event_repository import SeedListenEventRepository
from app.services.notification_delivery_service import NotificationDeliveryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_follow(
    channel_slug: str = "test-channel",
    notification_channel: str = "email",
    email: str | None = "fan@example.com",
    discord_user_id: str | None = None,
    confirmed: bool = True,
    notify_new_tracks: bool = True,
    notify_channel_live: bool = True,
    notify_digest: bool = False,
) -> FollowDocument:
    return FollowDocument(
        id=str(uuid4()),
        entity_type="channel",
        entity_id=channel_slug,
        channel_slug=channel_slug,
        notification_channel=notification_channel,
        email=email,
        discord_user_id=discord_user_id,
        confirmed=confirmed,
        created_at=_now(),
        code_used="TEST1",
        notify_new_tracks=notify_new_tracks,
        notify_channel_live=notify_channel_live,
        notify_digest=notify_digest,
    )


def _make_user(uid: str = "user-001", email: str = "fan@example.com") -> UserDocument:
    return UserDocument(
        id=uid,
        email=email,
        display_name="Test Fan",
        roles=[],
        created_at=_now(),
        is_active=True,
    )


def _make_delivery_svc(
    follow_repo: SeedFollowRepository | None = None,
    notif_repo: SeedNotificationRepository | None = None,
    throttle_repo: SeedThrottleRepository | None = None,
    user_repo: SeedUserRepository | None = None,
) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        follow_repo=follow_repo or SeedFollowRepository(),
        notif_repo=notif_repo or SeedNotificationRepository(),
        throttle_repo=throttle_repo or SeedThrottleRepository(),
        user_repo=user_repo or SeedUserRepository(),
        listen_history_svc=ListenHistoryService(SeedListenEventRepository()),
        settings=Settings(),
    )


def _make_admin_client(
    channel_svc: ChannelService | None = None,
    follow_repo: SeedFollowRepository | None = None,
    notif_repo: SeedNotificationRepository | None = None,
    delivery_svc: NotificationDeliveryService | None = None,
) -> TestClient:
    ch_svc = channel_svc or ChannelService(SeedChannelRepository())
    app.dependency_overrides[get_channel_service] = lambda: ch_svc
    app.dependency_overrides[get_current_admin] = lambda: {"sub": "admin"}
    if follow_repo is not None:
        app.dependency_overrides[get_follow_repository] = lambda: follow_repo
    if notif_repo is not None:
        app.dependency_overrides[get_notification_repository] = lambda: notif_repo
    if delivery_svc is not None:
        app.dependency_overrides[get_notification_delivery_service] = lambda: delivery_svc
    return TestClient(app, raise_server_exceptions=True)


def _make_follows_client(
    follow_repo: SeedFollowRepository,
    discord_id: str | None = None,
    email: str | None = "fan@example.com",
) -> TestClient:
    from app.api.dependencies import get_follow_service
    from app.services.follow_service import FollowService
    from app.repositories.channel_repository import SeedChannelRepository
    from app.repositories.code_repository import SeedCodeRepository

    svc = FollowService(follow_repo, SeedCodeRepository(), SeedChannelRepository())
    app.dependency_overrides[get_follow_service] = lambda: svc
    client = TestClient(app, raise_server_exceptions=True)
    if discord_id:
        client.cookies.set("wp_listener_discord_id", discord_id)
    if email:
        client.cookies.set("wp_listener_email", email)
    return client


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. FollowDocument schema defaults and backfill
# ---------------------------------------------------------------------------

def test_follow_document_notify_defaults():
    doc = _make_follow()
    assert doc.notify_new_tracks is True
    assert doc.notify_channel_live is True
    assert doc.notify_digest is False


def test_follow_document_backfill_from_old_data():
    """Pre-Slice-13 documents stored without notify_* fields get correct defaults."""
    raw = {
        "id": "f-001",
        "entity_type": "channel",
        "entity_id": "test-channel",
        "channel_slug": "test-channel",
        "notification_channel": "email",
        "email": "fan@example.com",
        "confirmed": True,
        "created_at": datetime.now(tz=timezone.utc),
        "code_used": "ABC123",
        # no notify_* fields
    }
    doc = FollowDocument(**raw)
    assert doc.notify_new_tracks is True
    assert doc.notify_channel_live is True
    assert doc.notify_digest is False


# ---------------------------------------------------------------------------
# 2. GET /api/follows — returns notify_* fields
# ---------------------------------------------------------------------------

def test_list_follows_includes_notify_fields():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(notify_digest=True)
    asyncio.run(follow_repo.create(follow))

    client = _make_follows_client(follow_repo, email=follow.email)
    resp = client.get("/api/follows")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["notify_new_tracks"] is True
    assert data[0]["notify_channel_live"] is True
    assert data[0]["notify_digest"] is True


# ---------------------------------------------------------------------------
# 3. PATCH /api/follows/{id} — update preferences
# ---------------------------------------------------------------------------

def test_patch_follow_updates_notify_prefs():
    follow_repo = SeedFollowRepository()
    follow = _make_follow()
    asyncio.run(follow_repo.create(follow))

    client = _make_follows_client(follow_repo, email=follow.email)
    resp = client.patch(
        f"/api/follows/{follow.id}",
        json={"notify_new_tracks": False, "notify_digest": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notify_new_tracks"] is False
    assert data["notify_digest"] is True
    assert data["notify_channel_live"] is True  # unchanged


def test_patch_follow_empty_body_422():
    follow_repo = SeedFollowRepository()
    follow = _make_follow()
    asyncio.run(follow_repo.create(follow))

    client = _make_follows_client(follow_repo, email=follow.email)
    resp = client.patch(f"/api/follows/{follow.id}", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. notify_new_tracks — email delivery
# ---------------------------------------------------------------------------

def test_notify_new_tracks_sends_email():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(channel_slug="lo-fi-beats")
    asyncio.run(follow_repo.create(follow))
    throttle_repo = SeedThrottleRepository()
    svc = _make_delivery_svc(follow_repo=follow_repo, throttle_repo=throttle_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug="lo-fi-beats",
                channel_name="Lo-Fi Beats",
                new_tracks=[{"title": "Chill Vibes", "artist": "DJ Zen", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/lo-fi-beats",
            )
        )

    assert result["sent"] == 1
    assert result["skipped"] == 0
    mock_send.assert_called_once()
    # Throttle should be recorded
    throttled = asyncio.run(
        throttle_repo.is_throttled(f"follow:{follow.id}", "lo-fi-beats", "new_tracks", 24)
    )
    assert throttled is True


def test_notify_new_tracks_skips_unconfirmed():
    """Unconfirmed follows are filtered by get_by_channel before delivery."""
    follow_repo = SeedFollowRepository()
    follow = _make_follow(confirmed=False)
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug=follow.channel_slug,
                channel_name="Test",
                new_tracks=[{"title": "Track", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/test-channel",
            )
        )

    # get_by_channel only returns confirmed=True, so unconfirmed never reaches delivery
    assert result["sent"] == 0
    mock_send.assert_not_called()


def test_notify_new_tracks_skips_opted_out():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(notify_new_tracks=False)
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug=follow.channel_slug,
                channel_name="Test",
                new_tracks=[{"title": "Track", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/test-channel",
            )
        )

    assert result["sent"] == 0
    mock_send.assert_not_called()


def test_notify_new_tracks_skips_throttled():
    follow_repo = SeedFollowRepository()
    follow = _make_follow()
    asyncio.run(follow_repo.create(follow))
    throttle_repo = SeedThrottleRepository()
    identity_key = f"follow:{follow.id}"
    asyncio.run(throttle_repo.record_sent(identity_key, follow.channel_slug, "new_tracks"))
    svc = _make_delivery_svc(follow_repo=follow_repo, throttle_repo=throttle_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug=follow.channel_slug,
                channel_name="Test",
                new_tracks=[{"title": "Track", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/test-channel",
            )
        )

    assert result["sent"] == 0
    assert result["skipped"] == 1
    mock_send.assert_not_called()


def test_notify_new_tracks_ignore_throttle():
    follow_repo = SeedFollowRepository()
    follow = _make_follow()
    asyncio.run(follow_repo.create(follow))
    throttle_repo = SeedThrottleRepository()
    asyncio.run(throttle_repo.record_sent(f"follow:{follow.id}", follow.channel_slug, "new_tracks"))
    svc = _make_delivery_svc(follow_repo=follow_repo, throttle_repo=throttle_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ):
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug=follow.channel_slug,
                channel_name="Test",
                new_tracks=[{"title": "Track", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/test-channel",
                ignore_throttle=True,
            )
        )

    assert result["sent"] == 1


# ---------------------------------------------------------------------------
# 5. notify_new_tracks — Discord DM delivery
# ---------------------------------------------------------------------------

def test_notify_new_tracks_discord_dm():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(
        notification_channel="discord",
        email=None,
        discord_user_id="discord-uid-999",
    )
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_discord_dm",
        new=AsyncMock(return_value=True),
    ) as mock_dm:
        result = asyncio.run(
            svc.notify_new_tracks(
                channel_slug=follow.channel_slug,
                channel_name="Test",
                new_tracks=[{"title": "Track", "url": "https://cdn/1.mp3"}],
                channel_url="http://localhost:3000/channels/test-channel",
            )
        )

    assert result["sent"] == 1
    mock_dm.assert_called_once()


# ---------------------------------------------------------------------------
# 6. send_weekly_digest
# ---------------------------------------------------------------------------

def test_digest_sends_email_to_digest_subscribers():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(notify_digest=True)
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(svc.send_weekly_digest())

    assert result["sent"] == 1
    mock_send.assert_called_once()


def test_digest_skips_discord_only_no_account():
    """Discord follow with no email field and no UserDocument → skipped."""
    follow_repo = SeedFollowRepository()
    follow = _make_follow(
        notification_channel="discord",
        email=None,
        discord_user_id="discord-uid-777",
        notify_digest=True,
    )
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(svc.send_weekly_digest())

    assert result["sent"] == 0
    mock_send.assert_not_called()


def test_digest_skips_non_digest_follows():
    follow_repo = SeedFollowRepository()
    follow = _make_follow(notify_digest=False)
    asyncio.run(follow_repo.create(follow))
    svc = _make_delivery_svc(follow_repo=follow_repo)

    with patch(
        "app.services.notification_delivery_service._send_resend_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        result = asyncio.run(svc.send_weekly_digest())

    assert result["sent"] == 0
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# 7. POST /api/admin/notifications/digest
# ---------------------------------------------------------------------------

def test_admin_digest_endpoint_calls_delivery_service():
    mock_svc = AsyncMock(spec=NotificationDeliveryService)
    mock_svc.send_weekly_digest.return_value = {"sent": 3, "skipped": 1}

    client = _make_admin_client(delivery_svc=mock_svc)
    resp = client.post("/api/admin/notifications/digest")
    assert resp.status_code == 200
    assert resp.json()["sent"] == 3
    mock_svc.send_weekly_digest.assert_called_once()


# ---------------------------------------------------------------------------
# 8. POST /api/admin/channels/{slug}/notify
# ---------------------------------------------------------------------------

def test_admin_manual_notify_404_unknown_channel():
    client = _make_admin_client()
    resp = client.post("/api/admin/channels/nonexistent/notify")
    assert resp.status_code == 404


def test_admin_manual_notify_returns_delivery_result():
    channel_repo = SeedChannelRepository()
    ch_svc = ChannelService(channel_repo)
    channels = asyncio.run(ch_svc.list_all())
    assert channels, "Seed channels must exist"
    slug = channels[0]["slug"]

    mock_delivery = AsyncMock(spec=NotificationDeliveryService)
    mock_delivery.notify_new_tracks.return_value = {"sent": 2, "skipped": 0}
    client = _make_admin_client(channel_svc=ch_svc, delivery_svc=mock_delivery)

    resp = client.post(f"/api/admin/channels/{slug}/notify")
    assert resp.status_code == 200
    assert resp.json()["sent"] == 2
    mock_delivery.notify_new_tracks.assert_called_once()
    call_kwargs = mock_delivery.notify_new_tracks.call_args.kwargs
    assert call_kwargs["ignore_throttle"] is True


# ---------------------------------------------------------------------------
# POST /api/codes/{code}/follow/me — one-click follow for logged-in users
# ---------------------------------------------------------------------------

def _make_follow_me_client(
    user: UserDocument,
    follow_repo: SeedFollowRepository | None = None,
) -> TestClient:
    from app.repositories.code_repository import SeedCodeRepository
    from app.services.code_service import CodeService
    from app.services.follow_service import FollowService

    code_repo = SeedCodeRepository()
    f_repo = follow_repo or SeedFollowRepository()
    channel_repo = SeedChannelRepository()
    code_svc = CodeService(code_repo, channel_repo)
    follow_svc = FollowService(f_repo, code_repo, channel_repo)

    app.dependency_overrides[get_code_service] = lambda: code_svc
    app.dependency_overrides[get_follow_service] = lambda: follow_svc
    app.dependency_overrides[get_current_user] = lambda: user

    # Seed a valid code
    asyncio.run(code_repo.create(_make_test_code()))

    return TestClient(app, raise_server_exceptions=True), code_repo, f_repo


def _make_test_code():
    from app.schemas.code import CodeDocument
    return CodeDocument(
        code="METEST",
        entity_type="channel",
        entity_id="test-channel",
        channel_slug="test-channel",
        active=True,
        created_at=_now(),
    )


def test_follow_as_me_email_user():
    """Email-only user → notification_channel=email, confirmed=True."""
    user = _make_user(uid="user-email-only", email="loggedin@example.com")
    client, _, follow_repo = _make_follow_me_client(user)

    resp = client.post("/api/codes/METEST/follow/me")
    assert resp.status_code == 201
    data = resp.json()
    assert data["confirmed"] is True
    assert data["channel"] == "email"

    follows = asyncio.run(follow_repo.get_by_channel("test-channel"))
    assert len(follows) == 1
    assert follows[0].email == "loggedin@example.com"
    assert follows[0].confirmed is True


def test_follow_as_me_discord_user():
    """User with discord_user_id → notification_channel=discord, confirmed=True."""
    user = UserDocument(
        id="user-discord",
        email="dj@example.com",
        display_name="DJ User",
        roles=[],
        created_at=_now(),
        is_active=True,
        discord_user_id="discord-999",
    )
    client, _, follow_repo = _make_follow_me_client(user)

    resp = client.post("/api/codes/METEST/follow/me")
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel"] == "discord"
    assert data["confirmed"] is True

    follows = asyncio.run(follow_repo.get_by_channel("test-channel"))
    assert follows[0].discord_user_id == "discord-999"


def test_follow_as_me_duplicate_returns_409():
    """Second follow from same user returns 409, not 500."""
    user = _make_user()
    client, _, _ = _make_follow_me_client(user)

    resp1 = client.post("/api/codes/METEST/follow/me")
    assert resp1.status_code == 201

    resp2 = client.post("/api/codes/METEST/follow/me")
    assert resp2.status_code == 409
    assert "already following" in resp2.json()["detail"].lower()
