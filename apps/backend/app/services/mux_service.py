"""Mux service: downloads cover (image or video loop) + audio from R2, runs
FFmpeg to produce a single MP4, uploads it back to R2, and returns the public URL.

The resulting MP4 is compatible with VRChat video players: H.264 video,
AAC audio, faststart flag for immediate playback.

Cover can be a still image (.jpg/.png) or a short looping video (.mp4/.mov).
When a video loop is supplied it repeats seamlessly for the full audio duration.

Channel info (title, host, genre, mood) is burned into the lower portion of
the frame via FFmpeg drawtext. Per-track "now playing" text is shown using
time-windowed enable='between(t,start,end)' entries — one per playlist track.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.repositories.channel_repository import ChannelRepository
from app.repositories.r2_repository import R2Repository
from app.schemas.sponsor import Sponsor, sponsor_is_live

logger = logging.getLogger("wavepalace.mux")

# Downscale all visual inputs to a fixed 720p canvas — bounds memory/CPU on
# Render and maximises VRChat compatibility regardless of source resolution.
_VIDEO_FILTER = (
    "scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"
)

_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

# Looping-video output framerate.
_LOOP_FPS = 15

# Hard cap so a runaway encode fails fast instead of hanging the worker.
_FFMPEG_TIMEOUT_S = 600


# ---------------------------------------------------------------------------
# Text overlay helpers
# ---------------------------------------------------------------------------

def _escape_drawtext(text: str) -> str:
    """Escape special characters for use as an FFmpeg drawtext text= value.

    Order matters: backslash must be escaped first so later replacements
    don't double-escape it.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


def _drawtext_overlay(
    title: str,
    host_name: str,
    genre: str,
    mood: str,
    font_path: str,
    track_times: list[tuple[float, float, str, str]] = (),
    sponsor_text: str = "",
    track_codes: list[tuple[float, float, str]] = (),
) -> str:
    """Return a comma-joined FFmpeg filter chain that burns channel info and
    per-track now-playing text into the bottom portion of a 1280×720 frame.

    Layout (bottom band, y=520–720):
      Row 1 (y=528): Channel title — static
      Row 2 (y=578): Hosted by … — static
      Row 3 left (y=618): Artist — Track — time-windowed per track
      Row 3 right (y=618): genre · mood — static
      Row 4 left (y=648): Sponsor text — static (optional)
      Row 4 right (y=650): LNHPROJ — time-windowed per track (fontsize=28)
      Row 5 right (y=692): wavepalace.live/follow — static

    Returns an empty string when the font file is not present so the mux still
    succeeds without text overlay.

    track_times: list of (start_secs, end_secs, track_title, track_artist)
    track_codes: list of (start_secs, end_secs, code_string)
    """
    regular = Path(font_path)
    if not regular.exists():
        logger.warning("Drawtext font not found at %s — overlay skipped", font_path)
        return ""

    bold_candidate = regular.parent / "DejaVuSans-Bold.ttf"
    bold = str(bold_candidate) if bold_candidate.exists() else str(regular)
    fp = str(regular)

    t = _escape_drawtext(title)
    h = _escape_drawtext(f"Hosted by {host_name}")
    gm = _escape_drawtext(f"{genre} · {mood}")

    shadow = "shadowx=1:shadowy=1:shadowcolor=black@0.80"

    parts = [
        # Dark band — 200px tall for 5 text rows.
        "drawbox=x=0:y=520:w=1280:h=200:color=black@0.50:t=fill",
        # Row 1: channel title.
        f"drawtext=fontfile={bold}:text={t}:x=24:y=528:fontsize=40:fontcolor=white:{shadow}",
        # Row 2: host credit.
        f"drawtext=fontfile={fp}:text={h}:x=24:y=578:fontsize=26:fontcolor=white@0.80:{shadow}",
        # Row 3 right: genre · mood pill — always visible.
        f"drawtext=fontfile={fp}:text={gm}:x=w-tw-24:y=618:fontsize=22:fontcolor=white@0.70:{shadow}",
        # Row 5 right: URL label — static, below code row.
        f"drawtext=fontfile={fp}:text=wavepalace.live/follow"
        f":x=w-tw-24:y=692:fontsize=16:fontcolor=white@0.45:{shadow}",
    ]

    # Row 4 left: sponsor lower-third — small, low-opacity.
    if sponsor_text:
        s = _escape_drawtext(sponsor_text)
        parts.append(
            f"drawtext=fontfile={fp}:text={s}:x=24:y=648:fontsize=18:fontcolor=white@0.55:{shadow}"
        )

    # Row 3 left: per-track now-playing — one entry per track, time-windowed.
    for start, end, track_title, track_artist in track_times:
        if not track_title and not track_artist:
            continue
        if track_artist and track_title:
            now_playing = _escape_drawtext(f"{track_artist} — {track_title}")  # em dash
        else:
            now_playing = _escape_drawtext(track_title or track_artist)
        parts.append(
            f"drawtext=fontfile={fp}:text={now_playing}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
            f":x=24:y=618:fontsize=22:fontcolor=white@0.90:{shadow}"
        )

    # Row 4 right: per-track code — bold, right-aligned, time-windowed.
    # Larger font (28) and positioned at y=650 so it sits clearly above the URL label.
    for start, end, code in track_codes:
        parts.append(
            f"drawtext=fontfile={bold}:text={_escape_drawtext(code)}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
            f":x=w-tw-24:y=650:fontsize=28:fontcolor=white@0.95:{shadow}"
        )

    return ",".join(parts)


# ---------------------------------------------------------------------------
# FFmpeg command builders
# ---------------------------------------------------------------------------

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
    cover: Path,
    audios: list[Path],
    output: Path,
    total_duration: float,
    overlay: str = "",
) -> list[str]:
    """Loop a still image at 1 fps over the concatenated playlist audio.

    *overlay* is a comma-joined drawtext filter chain (static + time-windowed)
    appended after the scale/pad chain so text is burned into every frame.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover)]
    for a in audios:
        cmd += ["-i", str(a)]

    vf_chain = f"{_VIDEO_FILTER},{overlay}" if overlay else _VIDEO_FILTER
    filter_complex = f"[0:v]{vf_chain}[vout];{_audio_concat_filter(len(audios))}"
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

    Overlay is NOT applied here — it is applied in _build_video_mux_cmd so
    time-windowed now-playing text works correctly across the full timeline.
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
    segment: Path,
    repeats: int,
    audios: list[Path],
    output: Path,
    total_duration: float,
    overlay: str = "",
) -> list[str]:
    """Stream-loop the pre-encoded *segment* and mux with concatenated audio.

    When *overlay* is provided the video is re-encoded (libx264 ultrafast) so
    the drawtext filter chain — including time-windowed per-track now-playing
    entries — is burned in.  Without overlay the video is stream-copied (zero
    re-encode cost).
    """
    cmd: list[str] = ["ffmpeg", "-y", "-stream_loop", str(repeats), "-i", str(segment)]
    for a in audios:
        cmd += ["-i", str(a)]

    if overlay:
        filter_complex = f"[0:v]{overlay}[vout];{_audio_concat_filter(len(audios))}"
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "1",
            "-c:a", "aac",
            "-b:a", "256k",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ]
    else:
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


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MuxService:
    def __init__(
        self,
        repository: ChannelRepository,
        r2: R2Repository,
        code_service=None,
    ) -> None:
        self._repository = repository
        self._r2 = r2
        self._code_service = code_service

    async def mux_channel(self, slug: str) -> str:
        """Mux cover + audio for *slug* and return the public MP4 URL."""
        channel = await self._repository.get_by_slug(slug)
        if channel is None:
            raise ValueError(f"Channel not found: {slug}")

        channel_id = channel["id"]
        cover_url = str(channel.get("visualLoopUrl") or channel["coverImageUrl"])

        # Build track list — support both new {url,title,artist} dicts and
        # legacy bare-string URLs (database backward-compat during migration).
        raw_playlist = channel.get("playlist") or []
        tracks_data: list[dict] = []
        for t in raw_playlist:
            if isinstance(t, dict):
                tracks_data.append({
                    "url": str(t.get("url", "")),
                    "title": str(t.get("title", "")),
                    "artist": str(t.get("artist", "")),
                })
            else:
                tracks_data.append({"url": str(t), "title": "", "artist": ""})

        if not tracks_data:
            tracks_data = [{"url": str(channel["audioUrl"]), "title": "", "artist": ""}]

        playlist_urls = [t["url"] for t in tracks_data]
        r2_key = f"muxed/{channel_id}/{slug}.mp4"

        logger.info("Muxing channel '%s'  cover=%s  tracks=%d", slug, cover_url, len(playlist_urls))

        settings = get_settings()

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
            for idx, track_url in enumerate(playlist_urls):
                track_path = tmp_path / f"track{idx}.mp3"
                try:
                    await asyncio.to_thread(_download, track_url, track_path)
                except Exception as exc:
                    raise RuntimeError(f"Download failed for track {track_url}: {exc}") from exc
                audio_paths.append(track_path)

            # Probe each track duration to build track_times for time-windowed
            # now-playing drawtext entries.
            total_duration = 0.0
            track_times: list[tuple[float, float, str, str]] = []
            cursor = 0.0
            for idx, p in enumerate(audio_paths):
                dur = await _probe_duration(p)
                meta = tracks_data[idx] if idx < len(tracks_data) else {}
                track_times.append((cursor, cursor + dur, meta.get("title", ""), meta.get("artist", "")))
                cursor += dur
                total_duration += dur

            if total_duration <= 0:
                raise RuntimeError(f"Could not determine audio duration for '{slug}'")

            # Generate and store one deterministic code per track.
            track_codes: list[tuple[float, float, str]] = []
            if self._code_service is not None:
                from app.services.code_service import make_mux_code
                for idx, (start, end, t_title, t_artist) in enumerate(track_times):
                    code = make_mux_code(slug, t_title, idx)
                    track_codes.append((start, end, code))
                    try:
                        await self._code_service.upsert_mux_code(
                            channel_slug=slug,
                            track_title=t_title,
                            track_artist=t_artist,
                            track_index=idx,
                        )
                    except Exception as exc:
                        logger.warning("Code upsert failed for %s track %d: %s", slug, idx, exc)

            # Resolve sponsor text for the drawtext overlay.
            _sp_raw = channel.get("sponsor")
            _sponsor_text = ""
            if _sp_raw:
                try:
                    _sp = Sponsor.model_validate(_sp_raw)
                    if sponsor_is_live(_sp):
                        _sponsor_text = _sp.text or f"Brought to you by {_sp.name}"
                except Exception:
                    pass

            def _join(val: object) -> str:
                return ", ".join(str(v) for v in val) if isinstance(val, list) else str(val or "")

            overlay = _drawtext_overlay(
                title=_join(channel.get("title", "")),
                host_name=_join(channel.get("hostName", "")),
                genre=_join(channel.get("genre", "")),
                mood=_join(channel.get("mood", "")),
                font_path=settings.font_path,
                track_times=track_times,
                sponsor_text=_sponsor_text,
                track_codes=track_codes,
            )

            if cover_path.suffix.lower() in _VIDEO_EXTS:
                # Encode raw normalized segment (no overlay — overlay goes in
                # final pass so time-windowed text spans the full timeline).
                seg_path = tmp_path / "seg.mp4"
                await _run_ffmpeg(_build_segment_cmd(cover_path, seg_path))
                seg_duration = await _probe_duration(seg_path)
                if seg_duration <= 0:
                    raise RuntimeError(f"Could not determine loop duration for '{slug}'")
                repeats = math.ceil(total_duration / seg_duration) + 1
                cmd = _build_video_mux_cmd(
                    seg_path, repeats, audio_paths, output_path, total_duration,
                    overlay=overlay,
                )
            else:
                cmd = _build_image_mux_cmd(
                    cover_path, audio_paths, output_path, total_duration, overlay=overlay
                )

            logger.info("Running: %s", " ".join(cmd))
            await _run_ffmpeg(cmd)

            public_url = await asyncio.to_thread(
                self._r2.upload_file, output_path, r2_key, "video/mp4", "public, max-age=60"
            )

        await self._repository.update(slug, {
            "vrchatPlaybackUrl": public_url,
            "muxOutdated": False,
            "muxLastAt": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Mux complete for '%s': %s", slug, public_url)
        return public_url

    async def published_slugs(self) -> list[str]:
        channels = await self._repository.list_channels()
        return [c["slug"] for c in channels if c.get("isPublished")]

    async def mux_all_published(self) -> dict[str, str]:
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


# ---------------------------------------------------------------------------
# Low-level I/O helpers
# ---------------------------------------------------------------------------

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
