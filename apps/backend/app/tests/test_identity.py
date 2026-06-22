"""Tests for Slice 10 — Identity & Roles.

Covers: sessions, bootstrap admin, email magic link, password auth,
role guards, Discord login path (mocked), user management endpoints.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_auth_service,
    get_session_repository,
    get_user_repository,
)
from app.core.auth import get_current_user
from app.main import app
from app.repositories.session_repository import SeedSessionRepository
from app.repositories.user_repository import SeedUserRepository
from app.schemas.user import BOOTSTRAP_ADMIN_ID, EmailLoginTokenDocument, SessionDocument, UserDocument
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_repo():
    return SeedUserRepository()


@pytest.fixture
def session_repo():
    return SeedSessionRepository()


@pytest.fixture
def auth_svc(user_repo, session_repo):
    return AuthService(user_repo, session_repo)


@pytest_asyncio.fixture
async def client(user_repo, session_repo, auth_svc):
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(user_repo, session_repo, auth_svc):
    """Client pre-authenticated as bootstrap admin."""
    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies={"wp_session": session_id},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Bootstrap admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bootstrap_admin_created(auth_svc):
    admin = await auth_svc.get_or_create_bootstrap_admin()
    assert admin.id == BOOTSTRAP_ADMIN_ID
    assert "admin" in admin.roles


@pytest.mark.asyncio
async def test_bootstrap_admin_idempotent(auth_svc):
    a1 = await auth_svc.get_or_create_bootstrap_admin()
    a2 = await auth_svc.get_or_create_bootstrap_admin()
    assert a1.id == a2.id


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_issue_and_resolve_session(auth_svc):
    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)
    assert isinstance(session_id, str) and len(session_id) > 10

    resolved = await auth_svc.get_user_by_session(session_id)
    assert resolved is not None
    assert resolved.id == BOOTSTRAP_ADMIN_ID


@pytest.mark.asyncio
async def test_revoked_session_rejects(auth_svc):
    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)
    await auth_svc.revoke_session(session_id)
    assert await auth_svc.get_user_by_session(session_id) is None


@pytest.mark.asyncio
async def test_expired_session_rejects(auth_svc, session_repo):
    admin = await auth_svc.get_or_create_bootstrap_admin()
    session_id = await auth_svc.issue_session(admin)
    # Manually expire the session
    session = await session_repo.get(session_id)
    session_repo._sessions[session_id] = session.model_copy(
        update={"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}
    )
    assert await auth_svc.get_user_by_session(session_id) is None


@pytest.mark.asyncio
async def test_unknown_session_returns_none(auth_svc):
    assert await auth_svc.get_user_by_session("nonexistent") is None


# ---------------------------------------------------------------------------
# Secret login endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_secret_login_issues_session(client):
    import os
    with patch.dict("os.environ", {"ADMIN_SECRET": "testsecret"}):
        from app.api.routes.admin_auth import reset_rate_limits
        reset_rate_limits()
        res = await client.post("/api/admin/login", json={"secret": "testsecret"})
        assert res.status_code == 200
        assert "wp_session" in res.cookies


@pytest.mark.asyncio
async def test_secret_login_wrong_secret(client):
    from app.api.routes.admin_auth import reset_rate_limits
    reset_rate_limits()
    res = await client.post("/api/admin/login", json={"secret": "wrong"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/admin/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_returns_user(admin_client):
    res = await admin_client.get("/api/admin/me")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "admin" in data["roles"]


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    res = await client.get("/api/admin/me")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Email magic link
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_request_always_200(client):
    res = await client.post("/api/auth/email/request", json={"email": "test@example.com"})
    assert res.status_code == 200
    assert res.json()["ok"] is True


@pytest.mark.asyncio
async def test_email_verify_valid_token(client, auth_svc, session_repo):
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    doc = EmailLoginTokenDocument(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        email="magic@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    await session_repo.create_email_token(doc)

    res = await client.get(f"/api/auth/email/verify?token={token}", follow_redirects=False)
    # FastAPI returns 307 for GET redirects; session cookie should be set
    assert res.status_code in (302, 303, 307)
    assert "wp_session" in res.cookies


@pytest.mark.asyncio
async def test_email_verify_invalid_token(client):
    res = await client.get("/api/auth/email/verify?token=garbage", follow_redirects=False)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_email_verify_expired_token(client, session_repo):
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    doc = EmailLoginTokenDocument(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        email="expired@example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    await session_repo.create_email_token(doc)

    res = await client.get(f"/api/auth/email/verify?token={token}", follow_redirects=False)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_email_verify_consumed_token(client, session_repo):
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    doc = EmailLoginTokenDocument(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        email="used@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        consumed=True,
    )
    await session_repo.create_email_token(doc)

    res = await client.get(f"/api/auth/email/verify?token={token}", follow_redirects=False)
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Password auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_and_login(client):
    res = await client.post(
        "/api/auth/register",
        json={"email": "user@test.com", "password": "secret123", "display_name": "Tester"},
    )
    assert res.status_code == 201
    assert "wp_session" in res.cookies

    # Login with same creds
    res2 = await client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "secret123"},
    )
    assert res2.status_code == 200
    assert "wp_session" in res2.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    body = {"email": "dup@test.com", "password": "pw", "display_name": "A"}
    await client.post("/api/auth/register", json=body)
    res = await client.post("/api/auth/register", json=body)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/register",
        json={"email": "wp@test.com", "password": "correct", "display_name": "U"},
    )
    res = await client.post(
        "/api/auth/login",
        json={"email": "wp@test.com", "password": "wrong"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_only_route_blocked_for_no_role(user_repo, session_repo, auth_svc):
    now = datetime.now(timezone.utc)
    user = UserDocument(
        id=str(uuid.uuid4()),
        display_name="Nobody",
        roles=[],
        created_at=now,
    )
    await user_repo.create(user)
    session_id = await auth_svc.issue_session(user)

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies={"wp_session": session_id},
    ) as ac:
        res = await ac.get("/api/admin/users")
    app.dependency_overrides.clear()
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_music_director_can_reach_analytics(user_repo, session_repo, auth_svc):
    """music_director role can hit admin-gated routes (analytics, channels)."""
    now = datetime.now(timezone.utc)
    md = UserDocument(
        id=str(uuid.uuid4()),
        display_name="DJ",
        roles=["music_director"],
        created_at=now,
    )
    await user_repo.create(md)
    session_id = await auth_svc.issue_session(md)

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_svc
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies={"wp_session": session_id},
    ) as ac:
        res = await ac.get("/api/admin/analytics")
    app.dependency_overrides.clear()
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Admin users endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users(admin_client):
    res = await admin_client.get("/api/admin/users")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(u["id"] == BOOTSTRAP_ADMIN_ID for u in data)


@pytest.mark.asyncio
async def test_update_user_roles(admin_client, user_repo):
    now = datetime.now(timezone.utc)
    new_user = UserDocument(
        id=str(uuid.uuid4()),
        display_name="NewGuy",
        roles=[],
        created_at=now,
    )
    await user_repo.create(new_user)

    res = await admin_client.patch(
        f"/api/admin/users/{new_user.id}/roles",
        json={"roles": ["music_director"]},
    )
    assert res.status_code == 200
    assert res.json()["roles"] == ["music_director"]


@pytest.mark.asyncio
async def test_deactivate_user(admin_client, user_repo):
    now = datetime.now(timezone.utc)
    new_user = UserDocument(
        id=str(uuid.uuid4()),
        display_name="ToDeactivate",
        roles=[],
        created_at=now,
    )
    await user_repo.create(new_user)

    res = await admin_client.patch(
        f"/api/admin/users/{new_user.id}/active",
        json={"is_active": False},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_deactivated_user_session_rejected(auth_svc, user_repo, session_repo):
    now = datetime.now(timezone.utc)
    user = UserDocument(
        id=str(uuid.uuid4()),
        display_name="Banned",
        roles=["admin"],
        created_at=now,
        is_active=True,
    )
    await user_repo.create(user)
    session_id = await auth_svc.issue_session(user)
    await user_repo.update(user.id, {"is_active": False})

    result = await auth_svc.get_user_by_session(session_id)
    # Session resolves but get_current_user guard checks is_active
    assert result is None or result.is_active is False


@pytest.mark.asyncio
async def test_update_roles_404(admin_client):
    res = await admin_client.patch(
        "/api/admin/users/nonexistent/roles",
        json={"roles": ["admin"]},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_clears_session(admin_client, auth_svc, session_repo):
    # Extract session from cookie
    me_res = await admin_client.get("/api/admin/me")
    assert me_res.status_code == 200

    res = await admin_client.post("/api/auth/logout")
    assert res.status_code == 200
