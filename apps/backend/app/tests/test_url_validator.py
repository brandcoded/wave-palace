"""Tests for Slice 5 URL validator service."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.services.url_validator import validate_urls


@pytest.mark.asyncio
async def test_non_https_rejected():
    results = await validate_urls(["http://example.com/track.mp3"], None)
    assert len(results) == 1
    r = results[0]
    assert not r.ok
    assert any("HTTPS" in w for w in r.warnings)


@pytest.mark.asyncio
async def test_https_audio_ok():
    with respx.mock:
        respx.head("https://example.com/track.mp3").mock(
            return_value=Response(200, headers={"content-type": "audio/mpeg"})
        )
        results = await validate_urls(["https://example.com/track.mp3"], None)
    assert results[0].ok
    assert results[0].warnings == []


@pytest.mark.asyncio
async def test_http_404_not_ok():
    with respx.mock:
        respx.head("https://example.com/missing.mp3").mock(
            return_value=Response(404)
        )
        results = await validate_urls(["https://example.com/missing.mp3"], None)
    assert not results[0].ok
    assert any("404" in w for w in results[0].warnings)


@pytest.mark.asyncio
async def test_head_405_falls_back_to_get():
    with respx.mock:
        respx.head("https://example.com/track.mp3").mock(
            return_value=Response(405)
        )
        respx.get("https://example.com/track.mp3").mock(
            return_value=Response(200, headers={"content-type": "audio/mpeg"})
        )
        results = await validate_urls(["https://example.com/track.mp3"], None)
    assert results[0].ok


@pytest.mark.asyncio
async def test_timeout_not_ok():
    import httpx

    with respx.mock:
        respx.head("https://example.com/slow.mp3").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        results = await validate_urls(["https://example.com/slow.mp3"], None)
    assert not results[0].ok
    assert any("timeout" in w.lower() for w in results[0].warnings)


@pytest.mark.asyncio
async def test_html_response_flagged():
    with respx.mock:
        respx.head("https://example.com/page").mock(
            return_value=Response(200, headers={"content-type": "text/html; charset=utf-8"})
        )
        results = await validate_urls(["https://example.com/page"], None)
    r = results[0]
    assert r.ok
    assert any("HTML" in w or "landing page" in w for w in r.warnings)


@pytest.mark.asyncio
async def test_video_mp4_passes():
    with respx.mock:
        respx.head("https://example.com/loop.mp4").mock(
            return_value=Response(200, headers={"content-type": "video/mp4"})
        )
        results = await validate_urls([], "https://example.com/loop.mp4")
    assert results[0].ok
    assert results[0].warnings == []


@pytest.mark.asyncio
async def test_non_mp4_video_warned():
    with respx.mock:
        respx.head("https://example.com/loop.webm").mock(
            return_value=Response(200, headers={"content-type": "video/webm"})
        )
        results = await validate_urls([], "https://example.com/loop.webm")
    r = results[0]
    assert r.ok
    assert any("MP4" in w or "VRChat" in w for w in r.warnings)


@pytest.mark.asyncio
async def test_r2_trusted_host_skips_content_type():
    with respx.mock:
        respx.head("https://stream.wavepalace.live/channels/test/loop.mp4").mock(
            return_value=Response(200, headers={"content-type": "application/octet-stream"})
        )
        results = await validate_urls(
            [], "https://stream.wavepalace.live/channels/test/loop.mp4"
        )
    assert results[0].ok
    assert results[0].warnings == []


@pytest.mark.asyncio
async def test_multiple_urls_concurrent():
    with respx.mock:
        respx.head("https://example.com/a.mp3").mock(
            return_value=Response(200, headers={"content-type": "audio/mpeg"})
        )
        respx.head("https://example.com/b.mp3").mock(
            return_value=Response(200, headers={"content-type": "audio/mpeg"})
        )
        respx.head("https://example.com/loop.mp4").mock(
            return_value=Response(200, headers={"content-type": "video/mp4"})
        )
        results = await validate_urls(
            ["https://example.com/a.mp3", "https://example.com/b.mp3"],
            "https://example.com/loop.mp4",
        )
    assert len(results) == 3
    assert all(r.ok for r in results)


@pytest.mark.asyncio
async def test_empty_urls_returns_empty():
    results = await validate_urls([], None)
    assert results == []


@pytest.mark.asyncio
async def test_one_failure_does_not_block_others():
    import httpx

    with respx.mock:
        respx.head("https://example.com/good.mp3").mock(
            return_value=Response(200, headers={"content-type": "audio/mpeg"})
        )
        respx.head("https://example.com/bad.mp3").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        results = await validate_urls(
            ["https://example.com/good.mp3", "https://example.com/bad.mp3"], None
        )
    assert len(results) == 2
    assert results[0].ok
    assert not results[1].ok
