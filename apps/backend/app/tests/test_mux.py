"""Tests for the mux service and mux API routes.

All external I/O (FFmpeg, file downloads, R2 uploads) is mocked so the
suite runs without network access, ffmpeg binary, or R2 credentials.
"""

from __future__ import annotations

import time
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
    """Return a MuxService whose mux methods are mocked."""
    svc = MagicMock(spec=MuxService)
    svc.mux_channel = AsyncMock(return_value=mux_result)
    svc.published_slugs = AsyncMock(return_value=["late-night-house"])
    svc.mux_all_published = AsyncMock(
        return_value={"late-night-house": mux_result}
    )
    return svc


@pytest.fixture()
def mux_client() -> TestClient:
    # Reset the module-level job stores so tests don't leak state into each other.
    from app.api.routes import mux as mux_routes
    mux_routes._JOB.update(running=False, started_at=None, finished_at=None, channels={})
    mux_routes._CHANNEL_JOBS.clear()

    svc = _make_mux_service()
    app.dependency_overrides[get_mux_service] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_mux_channel_returns_202(mux_client):
    res = mux_client.post("/api/channels/late-night-house/mux")
    assert res.status_code == 202
    body = res.json()
    assert body["slug"] == "late-night-house"
    assert body["status"] == "accepted"
    assert "poll" in body


def test_mux_channel_status_done(mux_client):
    """After the background task completes, status endpoint returns done + url."""
    mux_client.post("/api/channels/late-night-house/mux")
    res = mux_client.get("/api/channels/late-night-house/mux/status")
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "done"
    assert body["url"] == _FAKE_URL


def test_mux_channel_status_404_when_never_started(mux_client):
    res = mux_client.get("/api/channels/never-started/mux/status")
    assert res.status_code == 404


def test_mux_channel_409_when_already_running(mux_client):
    """Second POST while state is 'running' returns 409."""
    from app.api.routes import mux as mux_routes
    mux_routes._CHANNEL_JOBS["late-night-house"] = {
        "state": "running", "url": None, "error": None,
        "started_at": time.time(), "finished_at": None,
    }
    res = mux_client.post("/api/channels/late-night-house/mux")
    assert res.status_code == 409


def test_mux_channel_404_on_missing_slug(mux_client):
    """Service raises ValueError → background worker records error state."""
    svc = MagicMock(spec=MuxService)
    svc.mux_channel = AsyncMock(side_effect=ValueError("Channel not found: nope"))
    app.dependency_overrides[get_mux_service] = lambda: svc
    mux_client.post("/api/channels/nope/mux")
    status = mux_client.get("/api/channels/nope/mux/status").json()
    assert status["state"] == "error"
    assert "Channel not found" in status["error"]
    app.dependency_overrides.clear()


def test_mux_all_accepts_and_points_to_status(mux_client):
    res = mux_client.post("/api/mux/all")
    assert res.status_code == 202
    assert res.json()["status"] == "accepted"
    assert res.json()["poll"] == "/api/mux/status"


def test_mux_all_runs_background_and_records_status(mux_client):
    res = mux_client.post("/api/mux/all")
    assert res.status_code == 202

    status = mux_client.get("/api/mux/status").json()
    assert status["running"] is False
    assert status["channels"]["late-night-house"]["state"] == "done"
    assert status["channels"]["late-night-house"]["url"] == _FAKE_URL


def test_mux_status_records_per_channel_error(mux_client):
    svc = MagicMock(spec=MuxService)
    svc.published_slugs = AsyncMock(return_value=["broken"])
    svc.mux_channel = AsyncMock(side_effect=RuntimeError("ffmpeg failed"))
    app.dependency_overrides[get_mux_service] = lambda: svc

    mux_client.post("/api/mux/all")
    status = mux_client.get("/api/mux/status").json()
    assert status["channels"]["broken"]["state"] == "error"
    assert "ffmpeg failed" in status["channels"]["broken"]["error"]
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
        patch("app.services.mux_service._download"),
        patch("app.services.mux_service._run_ffmpeg", new_callable=AsyncMock) as mock_ff,
        patch("app.services.mux_service._probe_duration", new_callable=AsyncMock) as mock_probe,
        patch("app.services.mux_service.asyncio.to_thread") as mock_thread,
    ):
        mock_probe.return_value = 128.0
        async def fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

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


# ---------------------------------------------------------------------------
# Overlay / drawtext unit tests
# ---------------------------------------------------------------------------


def test_escape_drawtext_handles_special_chars():
    from app.services.mux_service import _escape_drawtext

    result = _escape_drawtext("It's Showtime: 100% Lit")
    assert "\\'" in result
    assert "\\:" in result
    assert "%%" in result


def test_escape_drawtext_escapes_backslash_first():
    from app.services.mux_service import _escape_drawtext

    assert _escape_drawtext("a\\b") == "a\\\\b"


def test_drawtext_overlay_empty_when_font_missing():
    from app.services.mux_service import _drawtext_overlay

    result = _drawtext_overlay("Title", "Host", "Genre", "Mood", "/nonexistent/font.ttf")
    assert result == ""


def test_drawtext_overlay_contains_title_host_genre_mood(tmp_path):
    from app.services.mux_service import _drawtext_overlay

    font = tmp_path / "DejaVuSans.ttf"
    font.write_bytes(b"fake")
    result = _drawtext_overlay("Late Night House", "DJ Skyy", "House", "Late Night", str(font))
    assert "Late Night House" in result
    assert "Hosted by DJ Skyy" in result
    assert "House" in result
    assert "Late Night" in result
    assert "drawbox" in result


def test_drawtext_overlay_includes_time_windowed_per_track(tmp_path):
    from app.services.mux_service import _drawtext_overlay

    font = tmp_path / "DejaVuSans.ttf"
    font.write_bytes(b"fake")
    track_times = [
        (0.0, 120.0, "Come Thru", "DJ Skyy"),
        (120.0, 250.0, "Day Trips", "DJ Skyy"),
    ]
    result = _drawtext_overlay("LNH", "DJ Skyy", "House", "Late Night", str(font), track_times)
    assert "between(t,0.000,120.000)" in result
    assert "between(t,120.000,250.000)" in result
    assert "Come Thru" in result
    assert "Day Trips" in result


def test_drawtext_overlay_skips_empty_track_titles(tmp_path):
    from app.services.mux_service import _drawtext_overlay

    font = tmp_path / "DejaVuSans.ttf"
    font.write_bytes(b"fake")
    track_times = [(0.0, 120.0, "", "")]
    result = _drawtext_overlay("LNH", "DJ", "House", "Late Night", str(font), track_times)
    assert "between(t" not in result


def test_build_image_mux_cmd_overlay_in_filter_complex(tmp_path):
    from app.services.mux_service import _build_image_mux_cmd

    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"x")
    audios = [tmp_path / "track0.mp3"]
    overlay = "drawbox=x=0:y=548:w=1280:h=172,drawtext=text=Come Thru"
    cmd = _build_image_mux_cmd(cover, audios, tmp_path / "out.mp4", 300.0, overlay=overlay)

    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "drawtext" in fc
    assert "Come Thru" in fc


def test_build_image_mux_cmd_no_overlay_no_drawtext():
    from app.services.mux_service import _build_image_mux_cmd

    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "drawtext" not in fc


def test_build_image_mux_cmd_concats_full_playlist():
    from app.services.mux_service import _build_image_mux_cmd

    cover = Path("/tmp/cover.jpg")
    audios = [Path(f"/tmp/track{i}.mp3") for i in range(4)]
    cmd = _build_image_mux_cmd(cover, audios, Path("/tmp/out.mp4"), total_duration=512.5)

    assert cmd.count("-i") == 5
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=4:v=0:a=1[aout]" in fc
    assert "-t" in cmd
    assert cmd[cmd.index("-t") + 1] == "512.500"
    assert "-shortest" not in cmd
    assert "-loop" in cmd


def test_build_segment_cmd_no_overlay():
    from app.services.mux_service import _build_segment_cmd

    cmd = _build_segment_cmd(Path("/tmp/loop.mp4"), Path("/tmp/seg.mp4"))
    vf = cmd[cmd.index("-vf") + 1]
    assert "drawtext" not in vf
    assert "scale=1280" in vf


def test_build_video_mux_cmd_no_overlay_uses_stream_copy():
    from app.services.mux_service import _build_video_mux_cmd

    cmd = _build_video_mux_cmd(
        Path("/tmp/seg.mp4"), 31, [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0
    )
    assert cmd[cmd.index("-c:v") + 1] == "copy"
    assert "drawtext" not in " ".join(cmd)
    assert cmd[cmd.index("-stream_loop") + 1] == "31"


def test_build_video_mux_cmd_with_overlay_reencodes(tmp_path):
    from app.services.mux_service import _build_video_mux_cmd

    overlay = "drawbox=x=0:y=548:w=1280:h=172,drawtext=text=Come Thru:enable='between(t,0.000,120.000)'"
    cmd = _build_video_mux_cmd(
        Path("/tmp/seg.mp4"), 31, [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        overlay=overlay,
    )
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "ultrafast" in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "drawtext" in fc
    assert "between(t" in fc


def test_build_video_mux_cmd_streamloops_segment():
    from app.services.mux_service import _build_video_mux_cmd

    seg = Path("/tmp/seg.mp4")
    audios = [Path(f"/tmp/track{i}.mp3") for i in range(4)]
    cmd = _build_video_mux_cmd(seg, repeats=31, audios=audios, output=Path("/tmp/out.mp4"), total_duration=889.6)

    assert cmd[cmd.index("-stream_loop") + 1] == "31"
    assert cmd[cmd.index("-t") + 1] == "889.600"
