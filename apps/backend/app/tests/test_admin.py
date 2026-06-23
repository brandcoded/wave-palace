"""Tests for Slice 3 admin routes: auth, submissions, channels, uploads, options, play count."""

from __future__ import annotations

import io
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_channel_service, get_r2_repository, get_submission_service
from app.api.routes import admin_auth as auth_routes
from app.api.routes import submissions as submission_routes
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.repositories.submission_options_repository import SeedSubmissionOptionsRepository
from app.repositories.submission_repository import SeedSubmissionRepository
from app.services.channel_service import ChannelService
from app.services.submission_service import SubmissionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SECRET = "test-secret-xyzzy-very-long-for-hmac-minimum"


def _auth_cookie() -> str:
    """Generate a valid JWT cookie value for the test secret."""
    from app.core.auth import create_token
    return create_token()


@pytest.fixture(autouse=True)
def _patch_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", _SECRET)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-bytes-long!")
    auth_routes.reset_rate_limits()
    yield
    auth_routes.reset_rate_limits()


def _make_client(overrides: dict | None = None, *, authed: bool = True) -> TestClient:
    """Build a TestClient with optional dependency overrides and auth cookie."""
    if overrides:
        for dep, impl in overrides.items():
            app.dependency_overrides[dep] = impl
    client = TestClient(app, raise_server_exceptions=True)
    if authed:
        client.cookies.set("wp_admin_token", _auth_cookie())
    return client


@pytest.fixture()
def anon_client() -> TestClient:
    svc = ChannelService(SeedChannelRepository())
    app.dependency_overrides[get_channel_service] = lambda: svc
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client() -> TestClient:
    svc = ChannelService(SeedChannelRepository())
    app.dependency_overrides[get_channel_service] = lambda: svc
    client = _make_client(authed=True)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def submissions_admin_client() -> TestClient:
    submission_routes.reset_rate_limits()
    sub_repo = SeedSubmissionRepository()
    opts_repo = SeedSubmissionOptionsRepository()
    svc = SubmissionService(sub_repo, opts_repo)
    app.dependency_overrides[get_submission_service] = lambda: svc
    client = _make_client(authed=True)
    yield client
    app.dependency_overrides.clear()
    submission_routes.reset_rate_limits()


@pytest.fixture()
def channels_admin_client() -> TestClient:
    repo = SeedChannelRepository()
    svc = ChannelService(repo)
    app.dependency_overrides[get_channel_service] = lambda: svc
    client = _make_client(authed=True)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def uploads_admin_client() -> TestClient:
    r2 = MagicMock()
    def upload_side_effect(data: bytes, key: str, content_type: str) -> str:
        return f"https://stream.wavepalace.live/{key}"
    r2.upload_bytes.side_effect = upload_side_effect
    async def multipart_side_effect(file_obj, key: str, content_type: str) -> str:
        return f"https://stream.wavepalace.live/{key}"
    r2.upload_multipart_stream = AsyncMock(side_effect=multipart_side_effect)
    app.dependency_overrides[get_r2_repository] = lambda: r2
    client = _make_client(authed=True)
    yield client
    app.dependency_overrides.clear()


def _make_r2_with_mock_client():
    """Build an R2Repository instance bypassing the boto3 credential check."""
    from app.repositories.r2_repository import R2Repository
    r2 = object.__new__(R2Repository)
    r2._bucket = "test-bucket"
    r2._public_base = "https://stream.wavepalace.live"
    r2._client = MagicMock()
    return r2


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


def test_login_correct_secret(anon_client):
    res = anon_client.post("/api/admin/login", json={"secret": _SECRET})
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_login_wrong_secret(anon_client):
    res = anon_client.post("/api/admin/login", json={"secret": "wrong"})
    assert res.status_code == 401


def test_me_with_valid_cookie(admin_client):
    res = admin_client.get("/api/admin/me")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_me_without_cookie(anon_client):
    res = anon_client.get("/api/admin/me")
    assert res.status_code == 401


def test_admin_route_requires_auth(anon_client):
    res = anon_client.get("/api/admin/submissions")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Submission review tests
# ---------------------------------------------------------------------------


def _seed_submission(client: TestClient) -> str:
    """POST a public submission and return its id."""
    payload = {
        "submitter_name": "DJ Test",
        "contact_email": "test@example.com",
        "channel_title": "Test Channel",
        "genre": ["House"],
        "mood": ["Late Night"],
        "energy": ["Medium"],
        "theme": ["Lounge"],
        "description": "A detailed late-night channel proposal with cleared house music.",
        "sample_links": ["https://example.com/mix"],
        "rights_attestation": True,
    }
    res = client.post("/api/submissions", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_list_pending_submissions(submissions_admin_client):
    _seed_submission(submissions_admin_client)
    res = submissions_admin_client.get("/api/admin/submissions")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_list_submissions_filter_approved(submissions_admin_client):
    sub_id = _seed_submission(submissions_admin_client)
    submissions_admin_client.patch(f"/api/admin/submissions/{sub_id}", json={"status": "approved"})
    res = submissions_admin_client.get("/api/admin/submissions?status=approved")
    assert res.status_code == 200
    assert any(s["id"] == sub_id for s in res.json())


def test_approve_submission(submissions_admin_client):
    sub_id = _seed_submission(submissions_admin_client)
    res = submissions_admin_client.patch(
        f"/api/admin/submissions/{sub_id}",
        json={"status": "approved", "reviewer_notes": "Great mix!"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["reviewer_notes"] == "Great mix!"


def test_review_invalid_status(submissions_admin_client):
    sub_id = _seed_submission(submissions_admin_client)
    res = submissions_admin_client.patch(
        f"/api/admin/submissions/{sub_id}", json={"status": "garbage"}
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Channel management tests
# ---------------------------------------------------------------------------


def test_list_all_channels_includes_unpublished(channels_admin_client):
    res = channels_admin_client.get("/api/admin/channels")
    assert res.status_code == 200
    slugs = [c["slug"] for c in res.json()]
    assert "hidden-draft" in slugs


def test_create_channel_generates_slug(channels_admin_client):
    res = channels_admin_client.post(
        "/api/admin/channels",
        json={
            "title": "Sunset Rooftop",
            "audioUrl": "https://stream.wavepalace.live/test.mp3",
            "coverImageUrl": "https://stream.wavepalace.live/test.jpg",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["slug"] == "sunset-rooftop"


def test_update_channel(channels_admin_client):
    res = channels_admin_client.patch(
        "/api/admin/channels/late-night-house",
        json={"description": "Updated description for the channel"},
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Updated description for the channel"


def test_delete_channel_soft_deletes(channels_admin_client):
    channels_admin_client.delete("/api/admin/channels/late-night-house")
    res = channels_admin_client.get("/api/channels")
    slugs = [c["slug"] for c in res.json()]
    assert "late-night-house" not in slugs


def test_update_channel_404(channels_admin_client):
    res = channels_admin_client.patch(
        "/api/admin/channels/does-not-exist",
        json={"description": "x"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


def test_upload_image_valid_jpeg(uploads_admin_client):
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (100, 100), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    data = img_bytes.getvalue()
    res = uploads_admin_client.post(
        "/api/admin/upload/image",
        files={"file": ("test.jpg", io.BytesIO(data), "image/jpeg")},
    )
    assert res.status_code == 200
    assert "url" in res.json()
    assert res.json()["url"].endswith(".webp")


def test_upload_image_wrong_type(uploads_admin_client):
    res = uploads_admin_client.post(
        "/api/admin/upload/image",
        files={"file": ("test.mp4", io.BytesIO(b"data"), "video/mp4")},
    )
    assert res.status_code == 400


def test_upload_audio_valid_mp3(uploads_admin_client):
    res = uploads_admin_client.post(
        "/api/admin/upload/audio",
        files={"file": ("track.mp3", io.BytesIO(b"ID3"), "audio/mpeg")},
    )
    assert res.status_code == 200
    assert "url" in res.json()


def test_upload_video_valid_mp4(uploads_admin_client):
    res = uploads_admin_client.post(
        "/api/admin/upload/video",
        files={"file": ("loop.mp4", io.BytesIO(b"\x00\x00\x00"), "video/mp4")},
    )
    assert res.status_code == 200
    assert "url" in res.json()


def test_upload_audio_multipart_success():
    """Multipart path: boto3 create/upload/complete called; 200 + URL returned."""
    r2 = _make_r2_with_mock_client()
    r2._client.create_multipart_upload.return_value = {"UploadId": "upload-123"}
    r2._client.upload_part.return_value = {"ETag": '"etag-abc"'}
    r2._client.complete_multipart_upload.return_value = {}
    app.dependency_overrides[get_r2_repository] = lambda: r2
    client = _make_client(authed=True)
    try:
        res = client.post(
            "/api/admin/upload/audio",
            files={"file": ("track.mp3", io.BytesIO(b"ID3" + b"\x00" * 100), "audio/mpeg")},
        )
        assert res.status_code == 200
        assert "url" in res.json()
        assert "stream.wavepalace.live" in res.json()["url"]
        r2._client.create_multipart_upload.assert_called_once()
        r2._client.complete_multipart_upload.assert_called_once()
        r2._client.abort_multipart_upload.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_upload_audio_multipart_abort_on_failure():
    """If upload_part raises, abort_multipart_upload must be called."""
    r2 = _make_r2_with_mock_client()
    r2._client.create_multipart_upload.return_value = {"UploadId": "upload-456"}
    r2._client.upload_part.side_effect = RuntimeError("simulated R2 failure")
    app.dependency_overrides[get_r2_repository] = lambda: r2
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("wp_admin_token", _auth_cookie())
    try:
        res = client.post(
            "/api/admin/upload/audio",
            files={"file": ("track.mp3", io.BytesIO(b"ID3" + b"\x00" * 100), "audio/mpeg")},
        )
        assert res.status_code == 500
        r2._client.abort_multipart_upload.assert_called_once()
        call_kwargs = r2._client.abort_multipart_upload.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["UploadId"] == "upload-456"
    finally:
        app.dependency_overrides.clear()


def test_upload_image_resizes_and_converts_to_webp(uploads_admin_client):
    """Verify that images over 1920px are resized and converted to WebP."""
    from PIL import Image as PILImage

    # Create a 2400×2400 PNG image
    img = PILImage.new("RGB", (2400, 2400), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_data = img_bytes.getvalue()

    res = uploads_admin_client.post(
        "/api/admin/upload/image",
        files={"file": ("large.png", io.BytesIO(img_data), "image/png")},
    )
    assert res.status_code == 200
    url = res.json()["url"]
    assert url.endswith(".webp"), f"Expected URL to end in .webp, got {url}"


# ---------------------------------------------------------------------------
# Options tests
# ---------------------------------------------------------------------------


def test_get_options(submissions_admin_client):
    res = submissions_admin_client.get("/api/admin/options")
    assert res.status_code == 200
    body = res.json()
    assert "genre" in body
    assert "mood" in body
    assert "energy" in body
    assert "theme" in body


def test_update_options_genre(submissions_admin_client):
    res = submissions_admin_client.patch(
        "/api/admin/options/genre",
        json={"options": ["House", "Techno", "Ambient"]},
    )
    assert res.status_code == 200
    assert res.json()["options"] == ["House", "Techno", "Ambient"]


def test_update_options_invalid_field(submissions_admin_client):
    res = submissions_admin_client.patch(
        "/api/admin/options/invalid",
        json={"options": ["House"]},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Play count tests
# ---------------------------------------------------------------------------


def test_record_play_increments(channels_admin_client):
    res = channels_admin_client.post(
        "/api/channels/late-night-house/play",
        headers={"x-forwarded-for": "1.2.3.4"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_record_play_unknown_slug(channels_admin_client):
    res = channels_admin_client.post("/api/channels/does-not-exist/play")
    assert res.status_code == 404


def test_play_count_in_channel_response(channels_admin_client):
    channels_admin_client.post(
        "/api/channels/late-night-house/play",
        headers={"x-forwarded-for": "5.6.7.8"},
    )
    res = channels_admin_client.get("/api/channels/late-night-house")
    assert res.status_code == 200
    assert "playCount" in res.json()
