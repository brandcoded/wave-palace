"""Mux service: downloads cover image + audio from R2, runs FFmpeg to produce
a single MP4, uploads it back to R2, and returns the public URL.

The resulting MP4 is compatible with VRChat video players: H.264 video
(static image looped), AAC audio, faststart flag for immediate playback.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import urllib.request
from pathlib import Path

from app.core.config import Settings
from app.repositories.channel_repository import ChannelRepository
from app.repositories.r2_repository import R2Repository

logger = logging.getLogger("wavepalace.mux")

# FFmpeg command template.
# -loop 1         : loop the single input image as video
# -shortest       : stop when the shorter stream (audio) ends
# -movflags +faststart : move moov atom to the front for streaming
_FFMPEG_CMD = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-framerate", "2",          # still image only needs a low fps
    "-i", "{cover}",
    "-i", "{audio}",
    "-c:v", "libx264",
    "-preset", "veryfast",      # fast encode so a single channel finishes in time
    "-tune", "stillimage",
    "-r", "2",                  # output 2 fps — tiny file, valid H.264 for VRChat
    "-c:a", "aac",
    "-b:a", "256k",
    "-pix_fmt", "yuv420p",
    "-shortest",
    "-movflags", "+faststart",
    "{output}",
]


class MuxService:
    def __init__(
        self,
        repository: ChannelRepository,
        r2: R2Repository,
    ) -> None:
        self._repository = repository
        self._r2 = r2

    async def mux_channel(self, slug: str) -> str:
        """Mux cover + audio for *slug* and return the public MP4 URL."""
        channel = await self._repository.get_by_slug(slug)
        if channel is None:
            raise ValueError(f"Channel not found: {slug}")

        channel_id = channel["id"]
        cover_url = str(channel["coverImageUrl"])
        audio_url = str(channel["audioUrl"])
        r2_key = f"muxed/{channel_id}/{slug}.mp4"

        logger.info("Muxing channel '%s'  cover=%s  audio=%s", slug, cover_url, audio_url)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cover_ext = Path(cover_url.split("?")[0]).suffix or ".jpg"
            cover_path = tmp_path / f"cover{cover_ext}"
            audio_path = tmp_path / "audio.mp3"
            output_path = tmp_path / "output.mp4"

            try:
                await asyncio.to_thread(_download, cover_url, cover_path)
            except Exception as exc:
                raise RuntimeError(f"Download failed for cover {cover_url}: {exc}") from exc
            try:
                await asyncio.to_thread(_download, audio_url, audio_path)
            except Exception as exc:
                raise RuntimeError(f"Download failed for audio {audio_url}: {exc}") from exc

            cmd = [
                part.format(
                    cover=str(cover_path),
                    audio=str(audio_path),
                    output=str(output_path),
                )
                for part in _FFMPEG_CMD
            ]
            logger.info("Running: %s", " ".join(cmd))
            await _run_ffmpeg(cmd)

            public_url = await asyncio.to_thread(
                self._r2.upload_file, output_path, r2_key, "video/mp4"
            )

        logger.info("Mux complete for '%s': %s", slug, public_url)
        return public_url

    async def published_slugs(self) -> list[str]:
        """Slugs of all published channels, in order."""
        channels = await self._repository.list_channels()
        return [c["slug"] for c in channels if c.get("isPublished")]

    async def mux_all_published(self) -> dict[str, str]:
        """Mux every published channel. Returns {slug: url} for successes and
        {slug: error_message} for failures."""
        channels = await self._repository.list_channels()
        results: dict[str, str] = {}
        for ch in channels:
            if not ch.get("isPublished"):
                continue
            slug = ch["slug"]
            try:
                url = await self.mux_channel(slug)
                results[slug] = url
            except Exception as exc:  # noqa: BLE001
                logger.error("Mux failed for '%s': %s", slug, exc)
                results[slug] = f"ERROR: {exc}"
        return results


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; WavePalace-Mux/1.0)"},
    )
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:  # noqa: S310
        f.write(resp.read())


async def _run_ffmpeg(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}):\n{stderr.decode()}")
