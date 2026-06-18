"""Mux service: downloads cover (image or video loop) + audio from R2, runs
FFmpeg to produce a single MP4, uploads it back to R2, and returns the public URL.

The resulting MP4 is compatible with VRChat video players: H.264 video,
AAC audio, faststart flag for immediate playback.

Cover can be a still image (.jpg/.png) or a short looping video (.mp4/.mov).
When a video loop is supplied it repeats seamlessly for the full audio duration.
"""

from __future__ import annotations

import asyncio
import logging
import math
import tempfile
import urllib.request
from pathlib import Path

from app.core.config import Settings
from app.repositories.channel_repository import ChannelRepository
from app.repositories.r2_repository import R2Repository

logger = logging.getLogger("wavepalace.mux")

# Downscale all visual inputs to a fixed 720p canvas — bounds memory/CPU on
# Render and maximises VRChat compatibility regardless of source resolution.
_VIDEO_FILTER = (
    "scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"
)

_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

# Looping-video output framerate. A background loop doesn't need 30 fps; 15 fps
# halves the file size and encode work.
_LOOP_FPS = 15

# Hard cap so a runaway encode fails fast instead of hanging the worker.
# Generous because a multi-track playlist can be 10+ minutes of audio and the
# video-loop path encodes a normalized segment plus a long AAC stream.
_FFMPEG_TIMEOUT_S = 600


def _audio_concat_filter(n: int, first_input: int = 1) -> str:
    """Filtergraph that normalizes and concatenates *n* audio inputs (starting
    at input index *first_input*) into a single [aout] stream."""
    norm = [
        f"[{first_input + i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}]"
        for i in range(n)
    ]
    concat_in = "".join(f"[a{i}]" for i in range(n))
    return ";".join(norm + [f"{concat_in}concat=n={n}:v=0:a=1[aout]"])


def _build_image_mux_cmd(
    cover: Path, audios: list[Path], output: Path, total_duration: float
) -> list[str]:
    """Loop a still image at 1 fps over the concatenated playlist audio.

    Output is bounded with -t so the looped image stops at the real end of the
    audio (with -filter_complex, -shortest does not terminate a looped image).
    """
    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover)]
    for a in audios:
        cmd += ["-i", str(a)]

    filter_complex = f"[0:v]{_VIDEO_FILTER}[vout];{_audio_concat_filter(len(audios))}"
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


def _build_segment_cmd(cover_video: Path, seg_out: Path) -> list[str]:
    """Re-encode the short loop clip ONCE to a normalized 720p H.264 segment.

    This is the only video re-encode in the video-loop path; the segment is
    then repeated via stream-copy (no re-encode), which keeps total CPU low
    enough to run on Render's free tier even for 10+ minute playlists.
    """
    return [
        "ffmpeg", "-y",
        "-i", str(cover_video),
        "-an",
        "-vf", _VIDEO_FILTER,
        "-r", str(_LOOP_FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-g", str(_LOOP_FPS * 2),
        "-threads", "1",
        str(seg_out),
    ]


def _build_video_mux_cmd(
    segment: Path, repeats: int, audios: list[Path], output: Path, total_duration: float
) -> list[str]:
    """Stream-loop the pre-encoded *segment* (video copy, no re-encode) over the
    concatenated playlist audio (AAC), bounded to *total_duration* with -t."""
    cmd: list[str] = ["ffmpeg", "-y", "-stream_loop", str(repeats), "-i", str(segment)]
    for a in audios:
        cmd += ["-i", str(a)]

    cmd += [
        "-filter_complex", _audio_concat_filter(len(audios)),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
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
        # Use the dedicated video loop when available; fall back to cover image.
        cover_url = str(channel.get("visualLoopUrl") or channel["coverImageUrl"])
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

            if cover_path.suffix.lower() in _VIDEO_EXTS:
                # Video loop: encode the clip once, then repeat it via stream-copy
                # so a long playlist stays within the free tier's CPU budget.
                seg_path = tmp_path / "seg.mp4"
                await _run_ffmpeg(_build_segment_cmd(cover_path, seg_path))
                seg_duration = await _probe_duration(seg_path)
                if seg_duration <= 0:
                    raise RuntimeError(f"Could not determine loop duration for '{slug}'")
                repeats = math.ceil(total_duration / seg_duration) + 1
                cmd = _build_video_mux_cmd(
                    seg_path, repeats, audio_paths, output_path, total_duration
                )
            else:
                cmd = _build_image_mux_cmd(
                    cover_path, audio_paths, output_path, total_duration
                )
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
