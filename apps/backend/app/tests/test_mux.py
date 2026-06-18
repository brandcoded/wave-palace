"""Tests for the mux service and mux API routes.

All external I/O (FFmpeg, file downloads, R2 uploads) is mocked so the
suite runs without network access, ffmpeg binary, or R2 credentials.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_mux_service
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.services.mux_service import MuxService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_FAKE_URL = "https://stream.wavepalace.live/muxed/channel_late_night_house/late-night-house.mp4"


def _make_mux_service(mux_result: str = _FAKE_URL) -> MuxService:
    """Return a MuxService whose mux_channel is mocked to return *mux_result*."""
    svc = MagicMock(spec=MuxService)
    svc.mux_channel = AsyncMock(return_value=mux_result)
    svc.mux_all_published = AsyncMock(
        return_value={"late-night-house": mux_result}
    )
    return svc


@pytest.fixture()
def mux_client() -> TestClient:
    svc = _make_mux_service()
    app.dependency_overrides[get_mux_service] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_mux_channel_returns_url(mux_client):
    res = mux_client.post("/api/channels/late-night-house/mux")
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "late-night-house"
    assert body["vrchatPlaybackUrl"] == _FAKE_URL


def test_mux_channel_404_on_missing_slug(mux_client):
    svc = MagicMock(spec=MuxService)
    svc.mux_channel = AsyncMock(side_effect=ValueError("Channel not found: nope"))
    app.dependency_overrides[get_mux_service] = lambda: svc
    res = mux_client.post("/api/channels/nope/mux")
    assert res.status_code == 404
    app.dependency_overrides.clear()


def test_mux_all_returns_results(mux_client):
    res = mux_client.post("/api/mux/all")
    assert res.status_code == 200
    body = res.json()
    assert "results" in body
    assert body["results"]["late-night-house"] == _FAKE_URL


def test_mux_all_500_on_runtime_error(mux_client):
    svc = MagicMock(spec=MuxService)
    svc.mux_all_published = AsyncMock(side_effect=RuntimeError("ffmpeg missing"))
    app.dependency_overrides[get_mux_service] = lambda: svc
    res = mux_client.post("/api/mux/all")
    assert res.status_code == 500
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# MuxService unit tests (mocked FFmpeg + R2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mux_service_mux_channel_happy_path():
    repo = SeedChannelRepository()
    r2 = MagicMock()
    r2.upload_file.return_value = _FAKE_URL
    svc = MuxService(repository=repo, r2=r2)

    with (
        patch("app.services.mux_service._download") as mock_dl,
        patch("app.services.mux_service._run_ffmpeg", new_callable=AsyncMock) as mock_ff,
        patch("app.services.mux_service.asyncio.to_thread") as mock_thread,
    ):
        # to_thread calls: _download (cover), _download (audio), r2.upload_file
        call_results = [None, None, _FAKE_URL]
        call_index = 0

        async def fake_to_thread(fn, *args, **kwargs):
            nonlocal call_index
            result = call_results[call_index]
            call_index += 1
            return result

        mock_thread.side_effect = fake_to_thread
        mock_ff.return_value = None

        url = await svc.mux_channel("late-night-house")

    assert url == _FAKE_URL


@pytest.mark.asyncio
async def test_mux_service_raises_on_missing_channel():
    repo = SeedChannelRepository()
    r2 = MagicMock()
    svc = MuxService(repository=repo, r2=r2)

    with pytest.raises(ValueError, match="Channel not found"):
        await svc.mux_channel("does-not-exist")


@pytest.mark.asyncio
async def test_mux_all_published_skips_unpublished():
    repo = SeedChannelRepository()
    r2 = MagicMock()
    svc = MuxService(repository=repo, r2=r2)

    with patch.object(svc, "mux_channel", new_callable=AsyncMock) as mock_mux:
        mock_mux.return_value = _FAKE_URL
        results = await svc.mux_all_published()

    # hidden-draft is unpublished — must not be in results
    assert "hidden-draft" not in results
    assert len(results) == 3


@pytest.mark.asyncio
async def test_mux_all_records_error_per_channel():
    repo = SeedChannelRepository()
    r2 = MagicMock()
    svc = MuxService(repository=repo, r2=r2)

    with patch.object(svc, "mux_channel", new_callable=AsyncMock) as mock_mux:
        mock_mux.side_effect = RuntimeError("ffmpeg not found")
        results = await svc.mux_all_published()

    assert all(v.startswith("ERROR:") for v in results.values())
