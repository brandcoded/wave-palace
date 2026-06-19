"""Media URL validation and VRChat compatibility checking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

TRUSTED_HOSTS = {"stream.wavepalace.live"}

AUDIO_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/wav",
    "application/octet-stream",
}

VIDEO_CONTENT_TYPES = {"video/mp4"}


class URLCheckResult(BaseModel):
    url: str
    ok: bool
    warnings: list[str]
    checked_at: datetime


def _is_trusted(url: str) -> bool:
    try:
        return urlparse(url).hostname in TRUSTED_HOSTS
    except Exception:
        return False


async def _check_one(url: str, is_video: bool) -> URLCheckResult:
    warnings: list[str] = []
    now = datetime.now(timezone.utc)

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return URLCheckResult(url=url, ok=False, warnings=["Not HTTPS"], checked_at=now)

    trusted = _is_trusted(url)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            try:
                resp = await client.head(url)
                if resp.status_code == 405:
                    resp = await client.get(url)
            except httpx.TimeoutException:
                return URLCheckResult(
                    url=url,
                    ok=False,
                    warnings=["Unreachable (timeout)"],
                    checked_at=now,
                )
            except httpx.RequestError as exc:
                return URLCheckResult(
                    url=url,
                    ok=False,
                    warnings=[f"Unreachable ({type(exc).__name__})"],
                    checked_at=now,
                )

        if resp.status_code >= 400:
            return URLCheckResult(
                url=url,
                ok=False,
                warnings=[f"HTTP {resp.status_code}"],
                checked_at=now,
            )

        if not trusted:
            ct = resp.headers.get("content-type", "").split(";")[0].strip().lower()

            if ct == "text/html":
                warnings.append("URL returns HTML — likely a landing page, not a direct file")

            if is_video:
                if ct and ct not in VIDEO_CONTENT_TYPES:
                    warnings.append("Not MP4 — VRChat may reject this video")
                elif not ct and not url.lower().endswith(".mp4"):
                    warnings.append("Not MP4 — VRChat may reject this video")
            else:
                if ct and ct not in AUDIO_CONTENT_TYPES and ct != "text/html":
                    warnings.append(f"Unexpected content-type: {ct}")

    except Exception as exc:
        return URLCheckResult(
            url=url,
            ok=False,
            warnings=[f"Unexpected error: {type(exc).__name__}"],
            checked_at=now,
        )

    return URLCheckResult(url=url, ok=True, warnings=warnings, checked_at=now)


async def validate_urls(
    audio_urls: list[str],
    visual_loop_url: str | None,
) -> list[URLCheckResult]:
    tasks: list[tuple[str, bool]] = [
        (u, False) for u in audio_urls if u
    ]
    if visual_loop_url:
        tasks.append((visual_loop_url, True))

    if not tasks:
        return []

    results = await asyncio.gather(
        *[_check_one(url, is_video) for url, is_video in tasks],
        return_exceptions=True,
    )

    out: list[URLCheckResult] = []
    now = datetime.now(timezone.utc)
    for (url, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            out.append(URLCheckResult(
                url=url,
                ok=False,
                warnings=[f"Internal error: {type(result).__name__}"],
                checked_at=now,
            ))
        else:
            out.append(result)

    return out
