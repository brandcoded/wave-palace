"""Tests for Slice 11 — Host Onboarding & Ownership.

Covers: Channel.owner_ids + auto_publish, invite generate/list/accept,
expiry + single-use guards, get_channels_by_owner, require_channel_owner.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_auth_service,
    get_channel_service,
    get_invite_service,
    get_session_repository,
    get_user_repository,
)
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.invite_repository import SeedInviteRepository
from app.repositories.session_repository import SeedSessionRepository
from app.repositories.user_repository import SeedUserRepository
from app.schemas.user import UserDocument
from app.services.auth_service import AuthService
from app.services.channel_service import ChannelService
from app.services.invite_service import InviteService

SLUG = "late-night-house"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def channel_repo():
    return SeedChannelRepository()


@pytest.fixture
def channel_service(channel_repo):
    return ChannelService(channel_repo)


@pytest.fixture
def invite_repo():
    return SeedInviteRepository()


@pytest.fixture
def invite_service(invite_repo, channel_repo):
    return InviteService(invite_repo, channel_repo)


@pytest.fixture
def user_repo():
    return SeedUserRepository()


@pytest.fixture
def session_repo():
    return SeedSessionRepository()


@pytest.fixture
def auth_svc(user_repo, session_repo):
    return AuthService(user_repo, session_repo)


def _overrides(channel_service, invite_service, user_repo, session_repo, auth_svc):
    app.dependency_overrides[get_channel_service] = lambda: channel_service
    app.dependency_overrides[get_invite_service] = lambda: invite_service
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_svc


async def _make_listener(auth_svc, user_repo, *, user_id="listener-1") -> str:
    """Create a plain (no-role) user, return a valid session id."""
    user = UserDocument(
        id=user_id,
        email=f"{user_id}@example.com",
        display_name="Listener",
        roles=[],
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    await user_repo.upsert(user)
    return await auth_svc.issue_session(user)


@pytest_asyncio.fixture
async def admin_client(channel_service, invite_service, user_repo, session_repo, auth_svc):
    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)
    _overrides(channel_service, invite_service, user_repo, session_repo, auth_svc)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver",
        cookies={"wp_session": session_id},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client(channel_service, invite_service, user_repo, session_repo, auth_svc):
    _overrides(channel_service, invite_service, user_repo, session_repo, auth_svc)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Schema fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_channel_has_owner_fields(admin_client):
    res = await admin_client.get("/api/admin/channels")
    assert res.status_code == 200
    ch = next(c for c in res.json() if c["slug"] == SLUG)
    assert "owner_ids" in ch
    assert "auto_publish" in ch


@pytest.mark.asyncio
async def test_patch_owner_ids(admin_client):
    res = await admin_client.patch(
        f"/api/admin/channels/{SLUG}", json={"owner_ids": ["user-xyz"]}
    )
    assert res.status_code == 200
    assert res.json()["owner_ids"] == ["user-xyz"]


@pytest.mark.asyncio
async def test_public_api_strips_owner_fields(anon_client):
    res = await anon_client.get(f"/api/channels/{SLUG}")
    assert res.status_code == 200
    body = res.json()
    assert "owner_ids" not in body
    assert "auto_publish" not in body


# ---------------------------------------------------------------------------
# get_channels_by_owner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_channels_by_owner(channel_service):
    await channel_service.update(SLUG, {"owner_ids": ["owner-1"]})
    owned = await channel_service.get_channels_by_owner("owner-1")
    assert len(owned) == 1
    assert owned[0]["slug"] == SLUG
    assert await channel_service.get_channels_by_owner("nobody") == []


# ---------------------------------------------------------------------------
# Invite generate / list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_invite(admin_client):
    res = await admin_client.post(f"/api/admin/channels/{SLUG}/invites")
    assert res.status_code == 201
    body = res.json()
    assert "token=" in body["invite_url"]
    assert body["channel_slug"] == SLUG


@pytest.mark.asyncio
async def test_generate_invite_unknown_channel(admin_client):
    res = await admin_client.post("/api/admin/channels/does-not-exist/invites")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_invites_no_raw_token(admin_client):
    await admin_client.post(f"/api/admin/channels/{SLUG}/invites")
    res = await admin_client.get(f"/api/admin/channels/{SLUG}/invites")
    assert res.status_code == 200
    invites = res.json()
    assert len(invites) == 1
    assert "token_hash" not in invites[0]
    assert "token" not in invites[0]


@pytest.mark.asyncio
async def test_generate_invite_requires_auth(anon_client):
    res = await anon_client.post(f"/api/admin/channels/{SLUG}/invites")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_generate_invite_forbidden_for_listener(
    anon_client, auth_svc, user_repo
):
    session_id = await _make_listener(auth_svc, user_repo)
    res = await anon_client.post(
        f"/api/admin/channels/{SLUG}/invites",
        cookies={"wp_session": session_id},
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Invite accept
# ---------------------------------------------------------------------------

async def _raw_token_for(invite_service, slug, by="admin"):
    _, raw = await invite_service.generate_invite(slug, by)
    return raw


@pytest.mark.asyncio
async def test_accept_invite_adds_owner(anon_client, invite_service, auth_svc, user_repo, channel_service):
    raw = await _raw_token_for(invite_service, SLUG)
    session_id = await _make_listener(auth_svc, user_repo, user_id="new-host")
    res = await anon_client.post(
        "/api/host/invite/accept",
        json={"token": raw},
        cookies={"wp_session": session_id},
    )
    assert res.status_code == 200
    assert res.json()["channel_slug"] == SLUG
    owned = await channel_service.get_channels_by_owner("new-host")
    assert len(owned) == 1


@pytest.mark.asyncio
async def test_accept_invite_requires_login(anon_client, invite_service):
    raw = await _raw_token_for(invite_service, SLUG)
    res = await anon_client.post("/api/host/invite/accept", json={"token": raw})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_accept_invite_unknown_token(anon_client, auth_svc, user_repo):
    session_id = await _make_listener(auth_svc, user_repo)
    res = await anon_client.post(
        "/api/host/invite/accept",
        json={"token": "garbage"},
        cookies={"wp_session": session_id},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_accept_invite_already_consumed(anon_client, invite_service, auth_svc, user_repo):
    raw = await _raw_token_for(invite_service, SLUG)
    s1 = await _make_listener(auth_svc, user_repo, user_id="host-a")
    first = await anon_client.post(
        "/api/host/invite/accept", json={"token": raw}, cookies={"wp_session": s1}
    )
    assert first.status_code == 200
    s2 = await _make_listener(auth_svc, user_repo, user_id="host-b")
    second = await anon_client.post(
        "/api/host/invite/accept", json={"token": raw}, cookies={"wp_session": s2}
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_expired(anon_client, invite_service, invite_repo, auth_svc, user_repo):
    _, raw = await invite_service.generate_invite(SLUG, "admin")
    # Force-expire the stored token.
    stored = invite_repo._invites[0]
    invite_repo._invites[0] = stored.model_copy(
        update={"expires_at": datetime.now(timezone.utc) - timedelta(days=1)}
    )
    session_id = await _make_listener(auth_svc, user_repo)
    res = await anon_client.post(
        "/api/host/invite/accept", json={"token": raw}, cookies={"wp_session": session_id}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_idempotent_same_user(invite_service, channel_service):
    raw = await _raw_token_for(invite_service, SLUG)
    await invite_service.accept_invite(raw, "same-user")
    # Re-accepting (token now consumed) must not duplicate ownership when bypassing
    # the consumed guard via a fresh token for the same user.
    raw2 = await _raw_token_for(invite_service, SLUG)
    await invite_service.accept_invite(raw2, "same-user")
    owned = await channel_service.get_channels_by_owner("same-user")
    assert len(owned) == 1
    raw_ch = await channel_service.get_raw_by_slug(SLUG)
    assert raw_ch["owner_ids"].count("same-user") == 1


# ---------------------------------------------------------------------------
# Channel owners endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_channel_owners(admin_client, channel_service, user_repo):
    await user_repo.upsert(
        UserDocument(
            id="owner-99",
            email="o99@example.com",
            display_name="Owner 99",
            roles=[],
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
    )
    await channel_service.update(SLUG, {"owner_ids": ["owner-99"]})
    res = await admin_client.get(f"/api/admin/channels/{SLUG}/owners")
    assert res.status_code == 200
    owners = res.json()
    assert len(owners) == 1
    assert owners[0]["display_name"] == "Owner 99"
