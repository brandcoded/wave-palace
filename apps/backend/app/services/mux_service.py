"""Mux service: downloads cover image + audio from R2, runs FFmpeg to produce
a single MP4, uploads it back to R2, and returns the public URL.

The resulting MP4 is compatible with VRChat video players: H.264 video
(static image looped), AAC audio, faststart flag for immediate playback.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import urllib.request
from pathlib import Path

from app.core.config import Settings
from app.repositories.channel_repository import ChannelRepository
from app.repositories.r2_repository import R2Repository

logger = logging.getLogger("wavepalace.mux")

# The MP4 contains the channel's ENTIRE playlist concatenated back-to-back over
# the cover image, so VRChat (which just plays one file) cycles through every
# track like the web player does.
#
# Source cover images vary in size (1024² up to 1536²+); encoding full-res
# frames OOM-kills Render's free tier. We downscale to a fixed 720p canvas so
# memory/CPU is bounded regardless of input, which is also the most
# VRChat-compatible resolution.
# -loop 1 image, 1 fps   : a still image needs only 1 fps (tiny, fast, valid H.264)
# concat filter          : join all playlist tracks (normalized to 44.1k stereo)
# -preset ultrafast      : minimal CPU on the throttled free tier
# -threads 1             : bound memory use
# -shortest              : stop the looped image when the (finite) audio ends
# -movflags +faststart   : move moov atom to the front for streaming
_VIDEO_FILTER = (
    "scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"
)

# Hard cap so a runaway encode fails fast instead of hanging the worker.
# Generous because a multi-track playlist can be 10+ minutes of audio.
_FFMPEG_TIMEOUT_S = 300


def _build_ffmpeg_cmd(
    cover: Path, audios: list[Path], output: Path, total_duration: float
) -> list[str]:
    """Build an ffmpeg command that loops *cover* as video and concatenates
    every track in *audios* into one continuous AAC stream.

    Output length is bounded with ``-t total_duration`` rather than
    ``-shortest``: with -filter_complex an infinitely-looped image never gets
    the EOF that -shortest needs, so the encode would run forever. -t stops it
    at the real end of the concatenated audio.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover)]
    for a in audios:
        cmd += ["-i", str(a)]

    n = len(audios)
    # Normalize each track so concat doesn't choke on differing sample rates,
    # then concatenate. Audio inputs are indices 1..n (0 is the cover image).
    norm = [
        f"[{i + 1}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}]"
        for i in range(n)
    ]
    concat_in = "".join(f"[a{i}]" for i in range(n))
    audio_chain = ";".join(norm + [f"{concat_in}concat=n={n}:v=0:a=1[aout]"])
    filter_complex = f"[0:v]{_VIDEO_FILTER}[vout];{audio_chain}"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-r", "1",
        "-threads", "1",
        "-c:a", "aac",
        "-b:a", "256k",
        "-t", f"{total_duration:.3f}",
        "-movflags", "+faststart",
        str(output),
    ]
    return cmd


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
        # Mux the whole playlist so VRChat cycles every track. Fall back to the
        # single audioUrl for channels without a playlist.
        playlist = [str(u) for u in (channel.get("playlist") or [])] or [str(channel["audioUrl"])]
        r2_key = f"muxed/{channel_id}/{slug}.mp4"

        logger.info("Muxing channel '%s'  cover=%s  tracks=%d", slug, cover_url, len(playlist))

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cover_ext = Path(cover_url.split("?")[0]).suffix or ".jpg"
            cover_path = tmp_path / f"cover{cover_ext}"
            output_path = tmp_path / "output.mp4"

            try:
                await asyncio.to_thread(_download, cover_url, cover_path)
            except Exception as exc:
                raise RuntimeError(f"Download failed for cover {cover_url}: {exc}") from exc

            audio_paths: list[Path] = []
            for idx, track_url in enumerate(playlist):
                track_path = tmp_path / f"track{idx}.mp3"
                try:
                    await asyncio.to_thread(_download, track_url, track_path)
                except Exception as exc:
                    raise RuntimeError(f"Download failed for track {track_url}: {exc}") from exc
                audio_paths.append(track_path)

            total_duration = 0.0
            for p in audio_paths:
                total_duration += await _probe_duration(p)
            if total_duration <= 0:
                raise RuntimeError(f"Could not determine audio duration for '{slug}'")

            cmd = _build_ffmpeg_cmd(cover_path, audio_paths, output_path, total_duration)
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


async def _probe_duration(path: Path) -> float:
    """Return the media duration in seconds via ffprobe (0.0 if unknown)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1",
        str(path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


async def _run_ffmpeg(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_FFMPEG_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"FFmpeg timed out after {_FFMPEG_TIMEOUT_S}s") from exc
    if proc.returncode != 0:
        tail = stderr.decode(errors="replace")[-800:]
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}):\n{tail}")
