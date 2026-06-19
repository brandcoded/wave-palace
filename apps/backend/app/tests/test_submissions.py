"""Tests for Slice 2 public submission routes."""

from __future__ import annotations

from itertools import count
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_r2_repository, get_submission_service
from app.main import app
from app.repositories.submission_options_repository import SeedSubmissionOptionsRepository
from app.repositories.submission_repository import SeedSubmissionRepository
from app.services.submission_service import SubmissionService


_ip_counter = count(1)


def _headers() -> dict[str, str]:
    return {"x-forwarded-for": f"192.0.2.{next(_ip_counter)}"}


def _valid_payload() -> dict:
    return {
        "submitter_name": "DJ Skyy",
        "contact_email": "skyy@example.com",
        "channel_title": "Afterhours Atrium",
        "profile_image_url": "https://stream.wavepalace.live/submissions/images/skyy.jpg",
        "genre": ["House"],
        "mood": ["Late Night"],
        "energy": ["Medium"],
        "theme": ["Lounge"],
        "description": "A late-night channel proposal with cleared house music.",
        "sample_links": ["https://example.com/mix"],
        "rights_attestation": True,
        "notes": "Available for launch curation.",
    }


@pytest.fixture()
def submissions_client() -> TestClient:
    from app.api.routes import submissions as submission_routes

    submission_routes.reset_rate_limits()
    service = SubmissionService(
        SeedSubmissionRepository(),
        SeedSubmissionOptionsRepository(),
    )
    r2 = MagicMock()
    r2.upload_bytes.return_value = (
        "https://stream.wavepalace.live/submissions/images/test.jpg"
    )
    app.dependency_overrides[get_submission_service] = lambda: service
    app.dependency_overrides[get_r2_repository] = lambda: r2
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    submission_routes.reset_rate_limits()


def test_get_submission_options_returns_seed_values(submissions_client):
    res = submissions_client.get("/api/submission-options")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "public, max-age=300"
    assert res.json() == {
        "genre": ["House", "Afro House", "Electronic"],
        "mood": ["Late Night", "Warm", "Dark"],
        "energy": ["Low", "Medium", "High"],
        "theme": ["Lounge", "Futuristic Lounge", "VR Party"],
    }


def test_upload_image_valid_jpeg_returns_url(submissions_client):
    res = submissions_client.post(
        "/api/submissions/upload-image",
        files={"file": ("profile.jpg", b"\xff\xd8\xff", "image/jpeg")},
        headers=_headers(),
    )
    assert res.status_code == 200
    assert res.json()["url"].startswith(
        "https://stream.wavepalace.live/submissions/images/"
    )


def test_upload_image_invalid_type_returns_400(submissions_client):
    res = submissions_client.post(
        "/api/submissions/upload-image",
        files={"file": ("profile.pdf", b"%PDF", "application/pdf")},
        headers=_headers(),
    )
    assert res.status_code == 400


def test_upload_image_too_large_returns_413(submissions_client):
    res = submissions_client.post(
        "/api/submissions/upload-image",
        files={"file": ("profile.jpg", b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")},
        headers=_headers(),
    )
    assert res.status_code == 413


def test_create_submission_valid_payload_returns_pending(submissions_client):
    res = submissions_client.post(
        "/api/submissions",
        json=_valid_payload(),
        headers=_headers(),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert body["id"]
    assert "Thanks DJ Skyy" in body["message"]


@pytest.mark.parametrize(
    ("field", "value", "expected_status"),
    [
        ("rights_attestation", False, 422),
        ("genre", ["Unknown"], 422),
        ("mood", ["Unknown"], 422),
        ("energy", ["Unknown"], 422),
        ("theme", ["Unknown"], 422),
        ("genre", [], 422),
        ("mood", [], 422),
        ("energy", [], 422),
        ("theme", [], 422),
        ("contact_email", "not-an-email", 422),
        ("sample_links", [], 422),
        ("sample_links", [f"https://example.com/{i}" for i in range(6)], 422),
        ("description", "Too short", 422),
        ("description", "x" * 501, 422),
    ],
)
def test_create_submission_validation_errors(
    submissions_client,
    field,
    value,
    expected_status,
):
    payload = _valid_payload()
    payload[field] = value
    res = submissions_client.post(
        "/api/submissions",
        json=payload,
        headers=_headers(),
    )
    assert res.status_code == expected_status


def test_create_submission_missing_required_field_returns_422(submissions_client):
    payload = _valid_payload()
    payload.pop("submitter_name")
    res = submissions_client.post(
        "/api/submissions",
        json=payload,
        headers=_headers(),
    )
    assert res.status_code == 422
