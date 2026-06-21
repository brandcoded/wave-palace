"""Tests for the DMCA / Copyright Takedown slice."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_takedown_service
from app.main import app
from app.repositories.takedown_repository import SeedTakedownRepository
from app.services.takedown_service import TakedownService

_VALID_BODY = {
    "claimant_name": "Jane Doe",
    "organization": "Doe Music Group",
    "email": "jane@example.com",
    "role": "artist",
    "song_name": "Projections",
    "artist_name": "DJ Skyy",
    "song_release_date": "2022",
    "channel_name": "Late Night House",
    "infringing_url": "https://wavepalace.live/channels/late-night-house",
    "description": "I own rights to 'Projections' by DJ Skyy.",
    "proof": "ISRC: USRC17607839",
    "electronic_signature": "Jane Doe",
    "good_faith": True,
    "accuracy": True,
}


@pytest.fixture()
def takedown_client():
    repo = SeedTakedownRepository()
    svc = TakedownService(repo)
    app.dependency_overrides[get_takedown_service] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/takedowns — submission
# ---------------------------------------------------------------------------

def test_submit_valid_returns_201(takedown_client):
    res = takedown_client.post("/api/takedowns", json=_VALID_BODY)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "submitted_at" in data


def test_submit_saves_record(takedown_client):
    takedown_client.post("/api/takedowns", json=_VALID_BODY)
    res = takedown_client.get("/api/takedowns")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["claimant_name"] == "Jane Doe"


def test_submit_missing_claimant_name_returns_422(takedown_client):
    body = {**_VALID_BODY}
    del body["claimant_name"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_submit_missing_email_returns_422(takedown_client):
    body = {**_VALID_BODY}
    del body["email"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_submit_missing_song_name_returns_422(takedown_client):
    body = {**_VALID_BODY}
    del body["song_name"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_submit_missing_artist_name_returns_422(takedown_client):
    body = {**_VALID_BODY}
    del body["artist_name"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_submit_missing_electronic_signature_returns_422(takedown_client):
    body = {**_VALID_BODY}
    del body["electronic_signature"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_good_faith_false_returns_422(takedown_client):
    body = {**_VALID_BODY, "good_faith": False}
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_accuracy_false_returns_422(takedown_client):
    body = {**_VALID_BODY, "accuracy": False}
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 422


def test_optional_fields_absent_is_valid(takedown_client):
    body = {
        k: v for k, v in _VALID_BODY.items()
        if k not in ("organization", "proof", "infringing_url", "song_release_date", "channel_name")
    }
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 201


def test_infringing_url_optional(takedown_client):
    body = {**_VALID_BODY}
    del body["infringing_url"]
    res = takedown_client.post("/api/takedowns", json=body)
    assert res.status_code == 201


def test_new_fields_stored(takedown_client):
    takedown_client.post("/api/takedowns", json=_VALID_BODY)
    items = takedown_client.get("/api/takedowns").json()
    assert items[0]["song_name"] == "Projections"
    assert items[0]["artist_name"] == "DJ Skyy"
    assert items[0]["electronic_signature"] == "Jane Doe"
    assert items[0]["channel_name"] == "Late Night House"


# ---------------------------------------------------------------------------
# GET /api/takedowns — list
# ---------------------------------------------------------------------------

def test_list_empty(takedown_client):
    res = takedown_client.get("/api/takedowns")
    assert res.status_code == 200
    assert res.json() == []


def test_list_returns_all(takedown_client):
    takedown_client.post("/api/takedowns", json=_VALID_BODY)
    takedown_client.post("/api/takedowns", json={**_VALID_BODY, "claimant_name": "Bob"})
    res = takedown_client.get("/api/takedowns")
    assert len(res.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/takedowns/{id}
# ---------------------------------------------------------------------------

def test_get_by_id(takedown_client):
    post = takedown_client.post("/api/takedowns", json=_VALID_BODY)
    takedown_id = post.json()["id"]
    res = takedown_client.get(f"/api/takedowns/{takedown_id}")
    assert res.status_code == 200
    assert res.json()["id"] == takedown_id
    assert res.json()["claimant_name"] == "Jane Doe"
    assert res.json()["status"] == "pending"


def test_get_by_id_not_found(takedown_client):
    res = takedown_client.get("/api/takedowns/nonexistent-id")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/takedowns/{id}/status
# ---------------------------------------------------------------------------

def test_status_update(takedown_client):
    post = takedown_client.post("/api/takedowns", json=_VALID_BODY)
    takedown_id = post.json()["id"]
    res = takedown_client.patch(
        f"/api/takedowns/{takedown_id}/status",
        json={"status": "reviewed", "notes": "Verified claim."},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "reviewed"
    assert res.json()["notes"] == "Verified claim."


def test_status_actioned(takedown_client):
    post = takedown_client.post("/api/takedowns", json=_VALID_BODY)
    takedown_id = post.json()["id"]
    res = takedown_client.patch(
        f"/api/takedowns/{takedown_id}/status",
        json={"status": "actioned"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "actioned"


def test_status_update_not_found(takedown_client):
    res = takedown_client.patch(
        "/api/takedowns/no-such-id/status",
        json={"status": "dismissed"},
    )
    assert res.status_code == 404


def test_status_invalid_value_returns_422(takedown_client):
    post = takedown_client.post("/api/takedowns", json=_VALID_BODY)
    takedown_id = post.json()["id"]
    res = takedown_client.patch(
        f"/api/takedowns/{takedown_id}/status",
        json={"status": "invalid-status"},
    )
    assert res.status_code == 422
