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
# Long DJ mixes (3-4 h) take 20-40 min on shared CPU — use 2-hour ceiling.
_FFMPEG_TIMEOUT_S = 7200


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
      Row 4 right (y=660): LNPROJ  ·  wavepalace.live  follow code — time-windowed per track

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

    # Row 4 right: per-track "CODE · wavepalace.live  follow code" — bold, right-aligned, time-windowed.
    for start, end, code in track_codes:
        label = _escape_drawtext(f"{code}  ·  wavepalace.live  follow code")
        parts.append(
            f"drawtext=fontfile={bold}:text={label}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
            f":x=w-tw-24:y=660:fontsize=22:fontcolor=white@0.85:{shadow}"
        )

    return ",".join(parts)


def _drawtext_split_screen(
    title: str,
    host_name: str,
    genre: str,
    mood: str,
    font_path: str,
    track_times: list[tuple[float, float, str, str]] = (),
    sponsor_text: str = "",
    track_codes: list[tuple[float, float, str]] = (),
) -> str:
    """Drawtext + drawbox filter chain for the split-screen layout (1280×720).

    Left panel (x 0–540): cover art with bottom scrim, channel title, host.
    Right panel (x 540–1280): dark #07050e, WavePalace logo, now-playing info,
    visualizer slot at y=220–340, genre/follow code at bottom.

    Returns "" when the font file is absent so the mux still completes.
    """
    regular = Path(font_path)
    if not regular.exists():
        logger.warning("Drawtext font not found at %s — overlay skipped", font_path)
        return ""

    bold_candidate = regular.parent / "DejaVuSans-Bold.ttf"
    bold = str(bold_candidate) if bold_candidate.exists() else str(regular)
    fp = str(regular)

    t  = _escape_drawtext(title)
    h  = _escape_drawtext(host_name)
    gm = _escape_drawtext(
        f"{genre} · {mood}" if (genre and mood) else (genre or mood)
    )

    shadow = "shadowx=1:shadowy=1:shadowcolor=black@0.80"
    LX = 18    # left panel text left-margin
    RX = 558   # right panel text left-margin
    RR = 1260  # right panel right-align anchor (x = RR - tw)

    parts = [
        # Left panel: bottom scrim (200px tall)
        f"drawbox=x=0:y=520:w={_SPLIT_LEFT_W}:h=200:color=black@0.72:t=fill",
        # Panel separator line
        f"drawbox=x={_SPLIT_LEFT_W - 2}:y=0:w=2:h={_SPLIT_FRAME_H}:color=white@0.10:t=fill",

        # Left: "CHANNEL" label
        f"drawtext=fontfile={bold}:text=CHANNEL:x={LX}:y=530:fontsize=13:fontcolor=#38e8ff:{shadow}",
        # Left: channel title
        f"drawtext=fontfile={bold}:text={t}:x={LX}:y=548:fontsize=32:fontcolor=white:{shadow}",
        # Left: "HOSTED BY" label
        f"drawtext=fontfile={fp}:text=HOSTED BY:x={LX}:y=592:fontsize=12:fontcolor=#ff5cc8:{shadow}",
        # Left: host name
        f"drawtext=fontfile={bold}:text={h}:x={LX}:y=608:fontsize=34:fontcolor=white:{shadow}",
        # Left: tagline
        f"drawtext=fontfile={fp}:text=Curated Vibes · Real Music · Always On"
        f":x={LX}:y=668:fontsize=11:fontcolor=white@0.40:{shadow}",

        # Right: WavePalace logo (top-right)
        f"drawtext=fontfile={bold}:text=WavePalace:x={RR}-tw:y=34:fontsize=22:fontcolor=#ece9ff:{shadow}",
        # Right: "NOW PLAYING" badge — 1px border box + label
        f"drawbox=x={RX - 2}:y=80:w=152:h=26:color=white@0.18:t=1",
        f"drawtext=fontfile={bold}:text=NOW PLAYING:x={RX + 6}:y=87:fontsize=12:fontcolor=#a78bfa:{shadow}",
    ]

    # Right: genre/mood (bottom-left of right panel)
    if gm:
        parts.append(
            f"drawtext=fontfile={fp}:text={gm}:x={RX}:y=670:fontsize=13:fontcolor=white@0.50:{shadow}"
        )

    # Right: wavepalace.live (bottom-right)
    parts.append(
        f"drawtext=fontfile={fp}:text=wavepalace.live:x={RR}-tw:y=670:fontsize=13:fontcolor=white@0.35:{shadow}"
    )

    # Right: sponsor credit (optional, small, below artist area)
    if sponsor_text:
        s = _escape_drawtext(sponsor_text)
        parts.append(
            f"drawtext=fontfile={fp}:text={s}:x={RX}:y=213:fontsize=12:fontcolor=white@0.50:{shadow}"
        )

    # Right: per-track title + artist (time-windowed)
    for start, end, track_title, track_artist in track_times:
        if track_title:
            tt = _escape_drawtext(track_title)
            parts.append(
                f"drawtext=fontfile={bold}:text={tt}"
                f":enable='between(t,{start:.3f},{end:.3f})'"
                f":x={RX}:y=124:fontsize=46:fontcolor=#ece9ff:{shadow}"
            )
        if track_artist:
            ta = _escape_drawtext(track_artist)
            parts.append(
                f"drawtext=fontfile={fp}:text={ta}"
                f":enable='between(t,{start:.3f},{end:.3f})'"
                f":x={RX}:y=180:fontsize=20:fontcolor=#a78bfa:{shadow}"
            )

    # Right: per-track follow code (time-windowed, bottom-right)
    for start, end, code in track_codes:
        label = _escape_drawtext(f"{code}  ·  follow code")
        parts.append(
            f"drawtext=fontfile={bold}:text={label}"
            f":enable='between(t,{start:.3f},{end:.3f})'"
            f":x={RR}-tw:y=648:fontsize=14:fontcolor=white@0.80:{shadow}"
        )

    return ",".join(parts)


# ---------------------------------------------------------------------------
# Visualizer filter helpers (VRChat mux — audioMotion-style log-freq spectrum)
# ---------------------------------------------------------------------------

# All visualizer styles composite into a uniform full-width 1280×120 strip
# centered vertically in the 720p canvas (y = (720 - 120) / 2 = 300).
_VIZ_POSITION = "0:300"

# Theme name → hex RGB color used by the FFmpeg filter.
_THEME_COLOR: dict[str, str] = {
    "violet":    "0xa78bfa",
    "teal":      "0x2dd4bf",
    "ember":     "0xfb923c",
    "rose":      "0xfb7185",
    "ice":       "0xbae6fd",
    # "frequency" is a per-bin gradient in the browser; mux uses a neutral green.
    "frequency": "0x22c55e",
}


def _hex_to_rgb_normalized(hex_str: str) -> tuple[float, float, float]:
    """Convert '0xrrggbb' to normalized (r, g, b) floats in [0, 1]."""
    h = hex_str.replace("0x", "").replace("#", "")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def _viz_filter(style: str, theme: str, width: int = 1280) -> str | None:
    """Return an FFmpeg lavfi filter string for *style* + *theme*.

    Produces a {width}×120 output intended to be composited via overlay.
    Default width 1280 covers the full-bleed layout; pass a narrower value
    (e.g. 740) to confine the strip to the right panel in split-screen.
    Returns None for style "none" or unknown values.
    """
    if not style or style == "none":
        return None
    color = _THEME_COLOR.get(theme, _THEME_COLOR["violet"])
    size = f"{width}x120"
    if style == "bars":
        return f"showfreqs=s={size}:mode=bar:fscale=log:ascale=log:colors={color}@0.85"
    if style == "terrain":
        # showfreqs supports only line/bar/dot; "bar2" is not valid.
        return f"showfreqs=s={size}:mode=dot:fscale=log:ascale=log:colors={color}@0.70"
    if style == "waveform":
        return f"showfreqs=s={size}:mode=line:fscale=log:ascale=log:colors={color}@0.80"
    if style in ("blob", "circular"):
        r, g, b = _hex_to_rgb_normalized(color)
        return (
            f"showcqt=s={size}:bar_g=2:count=1:tc=0.33,"
            f"colorchannelmixer=rr={r:.3f}:gg={g:.3f}:bb={b:.3f}"
        )
    return None


# ---------------------------------------------------------------------------
# Split-screen layout constants
# ---------------------------------------------------------------------------

# 1280×720 canvas: left 540px = cover art, right 740px = dark info panel.
_SPLIT_LEFT_W = 540
_SPLIT_RIGHT_W = 740   # 1280 - 540
_SPLIT_FRAME_W = 1280
_SPLIT_FRAME_H = 720

# Left panel filter: fill-crop cover to 540×720, pad right with dark bg.
_SPLIT_COVER_FILTER = (
    f"scale={_SPLIT_LEFT_W}:{_SPLIT_FRAME_H}:force_original_aspect_ratio=increase,"
    f"crop={_SPLIT_LEFT_W}:{_SPLIT_FRAME_H},"
    f"pad={_SPLIT_FRAME_W}:{_SPLIT_FRAME_H}:0:0:color=#07050e,"
    "setsar=1,format=yuv420p"
)


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
    viz_style: str = "none",
    viz_theme: str = "violet",
) -> list[str]:
    """Loop a still image at 1 fps over the concatenated playlist audio.

    *overlay* is a comma-joined drawtext filter chain (static + time-windowed)
    appended after the scale/pad chain so text is burned into every frame.
    *viz_style* + *viz_theme* add an audio-reactive FFmpeg filter overlaid at
    the bottom of the frame.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover)]
    for a in audios:
        cmd += ["-i", str(a)]

    vf_chain = f"{_VIDEO_FILTER},{overlay}" if overlay else _VIDEO_FILTER
    audio_part = _audio_concat_filter(len(audios))

    viz_f = _viz_filter(viz_style, viz_theme)
    if viz_f is not None:
        filter_complex = (
            f"[0:v]{vf_chain}[vout];"
            f"{audio_part};"
            f"[aout]asplit=2[aout_play][aout_viz];"
            f"[aout_viz]{viz_f}[vizout];"
            f"[vout][vizout]overlay={_VIZ_POSITION}[final_v]"
        )
        vid_map, aud_map = "[final_v]", "[aout_play]"
    else:
        filter_complex = f"[0:v]{vf_chain}[vout];{audio_part}"
        vid_map, aud_map = "[vout]", "[aout]"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", vid_map,
        "-map", aud_map,
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
    viz_style: str = "none",
    viz_theme: str = "violet",
) -> list[str]:
    """Stream-loop the pre-encoded *segment* and mux with concatenated audio.

    When *overlay* is provided the video is re-encoded (libx264 ultrafast) so
    the drawtext filter chain — including time-windowed per-track now-playing
    entries — is burned in.  Without overlay the video is stream-copied (zero
    re-encode cost).  *viz_style* + *viz_theme* add an audio-reactive FFmpeg
    filter overlay at the bottom of the frame.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-stream_loop", str(repeats), "-i", str(segment)]
    for a in audios:
        cmd += ["-i", str(a)]

    viz_f = _viz_filter(viz_style, viz_theme)
    audio_part = _audio_concat_filter(len(audios))

    if overlay and viz_f is not None:
        filter_complex = (
            f"[0:v]{overlay}[vout];"
            f"{audio_part};"
            f"[aout]asplit=2[aout_play][aout_viz];"
            f"[aout_viz]{viz_f}[vizout];"
            f"[vout][vizout]overlay={_VIZ_POSITION}[final_v]"
        )
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[final_v]",
            "-map", "[aout_play]",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "1",
            "-c:a", "aac", "-b:a", "256k",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ]
    elif overlay:
        filter_complex = f"[0:v]{overlay}[vout];{audio_part}"
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "1",
            "-c:a", "aac", "-b:a", "256k",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ]
    elif viz_f is not None:
        filter_complex = (
            f"{audio_part};"
            f"[aout]asplit=2[aout_play][aout_viz];"
            f"[aout_viz]{viz_f}[vizout];"
            f"[0:v][vizout]overlay={_VIZ_POSITION}[final_v]"
        )
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[final_v]",
            "-map", "[aout_play]",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "1",
            "-c:a", "aac", "-b:a", "256k",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ]
    else:
        cmd += [
            "-filter_complex", audio_part,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k",
            "-t", f"{total_duration:.3f}",
            "-movflags", "+faststart",
            str(output),
        ]
    return cmd


# ---------------------------------------------------------------------------
# Split-screen command builders
# ---------------------------------------------------------------------------

def _build_split_segment_cmd(cover_video: Path, seg_out: Path) -> list[str]:
    """Re-encode the loop clip for split-screen: 540×720 fill-crop segment."""
    return [
        "ffmpeg", "-y",
        "-i", str(cover_video),
        "-an",
        "-vf", (
            f"scale={_SPLIT_LEFT_W}:{_SPLIT_FRAME_H}:force_original_aspect_ratio=increase,"
            f"crop={_SPLIT_LEFT_W}:{_SPLIT_FRAME_H},"
            "setsar=1,format=yuv420p"
        ),
        "-r", str(_LOOP_FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-g", str(_LOOP_FPS * 2),
        "-threads", "1",
        str(seg_out),
    ]


def _build_image_split_screen_cmd(
    cover: Path,
    audios: list[Path],
    output: Path,
    total_duration: float,
    overlay: str = "",
    viz_style: str = "none",
    viz_theme: str = "violet",
) -> list[str]:
    """Still-image split-screen mux: cover fills left 540px, dark right panel.

    Visualizer strip (if any) is 740px wide, positioned in the right panel
    at y=220 (below the artist line, above the bottom tags).
    """
    cmd: list[str] = ["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover)]
    for a in audios:
        cmd += ["-i", str(a)]

    base_vf = f"{_SPLIT_COVER_FILTER},{overlay}" if overlay else _SPLIT_COVER_FILTER
    audio_part = _audio_concat_filter(len(audios))
    viz_f = _viz_filter(viz_style, viz_theme, width=_SPLIT_RIGHT_W)
    viz_pos = f"{_SPLIT_LEFT_W}:220"

    if viz_f is not None:
        filter_complex = (
            f"[0:v]{base_vf}[vout];"
            f"{audio_part};"
            f"[aout]asplit=2[aout_play][aout_viz];"
            f"[aout_viz]{viz_f}[vizout];"
            f"[vout][vizout]overlay={viz_pos}[final_v]"
        )
        vid_map, aud_map = "[final_v]", "[aout_play]"
    else:
        filter_complex = f"[0:v]{base_vf}[vout];{audio_part}"
        vid_map, aud_map = "[vout]", "[aout]"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", vid_map,
        "-map", aud_map,
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


def _build_video_split_screen_cmd(
    segment: Path,
    repeats: int,
    audios: list[Path],
    output: Path,
    total_duration: float,
    overlay: str = "",
    viz_style: str = "none",
    viz_theme: str = "violet",
) -> list[str]:
    """Stream-loop a 540×720 segment, pad to 1280×720, apply split-screen overlay."""
    cmd: list[str] = ["ffmpeg", "-y", "-stream_loop", str(repeats), "-i", str(segment)]
    for a in audios:
        cmd += ["-i", str(a)]

    pad_vf = (
        f"pad={_SPLIT_FRAME_W}:{_SPLIT_FRAME_H}:0:0:color=#07050e,"
        "setsar=1,format=yuv420p"
    )
    base_vf = f"{pad_vf},{overlay}" if overlay else pad_vf
    audio_part = _audio_concat_filter(len(audios))
    viz_f = _viz_filter(viz_style, viz_theme, width=_SPLIT_RIGHT_W)
    viz_pos = f"{_SPLIT_LEFT_W}:220"

    if viz_f is not None:
        filter_complex = (
            f"[0:v]{base_vf}[vout];"
            f"{audio_part};"
            f"[aout]asplit=2[aout_play][aout_viz];"
            f"[aout_viz]{viz_f}[vizout];"
            f"[vout][vizout]overlay={viz_pos}[final_v]"
        )
        cmd += ["-filter_complex", filter_complex, "-map", "[final_v]", "-map", "[aout_play]"]
    else:
        filter_complex = f"[0:v]{base_vf}[vout];{audio_part}"
        cmd += ["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"]

    cmd += [
        "-c:v", "libx264", "-preset", "ultrafast",
        "-threads", "1",
        "-c:a", "aac", "-b:a", "256k",
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

            renderer_template: str = channel.get("renderer_template") or "split-screen"
            is_split = renderer_template == "split-screen"
            viz_style: str = channel.get("visualizer_style") or "none"
            viz_theme: str = channel.get("visualizer_theme") or "violet"

            common_kw = dict(
                title=_join(channel.get("title", "")),
                host_name=_join(channel.get("hostName", "")),
                genre=_join(channel.get("genre", "")),
                mood=_join(channel.get("mood", "")),
                font_path=settings.font_path,
                track_times=track_times,
                sponsor_text=_sponsor_text,
                track_codes=track_codes,
            )
            text_overlay = (
                _drawtext_split_screen(**common_kw)
                if is_split
                else _drawtext_overlay(**common_kw)
            )

            if cover_path.suffix.lower() in _VIDEO_EXTS:
                seg_path = tmp_path / "seg.mp4"
                await _run_ffmpeg(
                    _build_split_segment_cmd(cover_path, seg_path)
                    if is_split
                    else _build_segment_cmd(cover_path, seg_path)
                )
                seg_duration = await _probe_duration(seg_path)
                if seg_duration <= 0:
                    raise RuntimeError(f"Could not determine loop duration for '{slug}'")
                repeats = math.ceil(total_duration / seg_duration) + 1
                cmd = (
                    _build_video_split_screen_cmd(
                        seg_path, repeats, audio_paths, output_path, total_duration,
                        overlay=text_overlay, viz_style=viz_style, viz_theme=viz_theme,
                    )
                    if is_split
                    else _build_video_mux_cmd(
                        seg_path, repeats, audio_paths, output_path, total_duration,
                        overlay=text_overlay, viz_style=viz_style, viz_theme=viz_theme,
                    )
                )
            else:
                cmd = (
                    _build_image_split_screen_cmd(
                        cover_path, audio_paths, output_path, total_duration,
                        overlay=text_overlay, viz_style=viz_style, viz_theme=viz_theme,
                    )
                    if is_split
                    else _build_image_mux_cmd(
                        cover_path, audio_paths, output_path, total_duration,
                        overlay=text_overlay, viz_style=viz_style, viz_theme=viz_theme,
                    )
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
        while chunk := resp.read(8 * 1024 * 1024):  # 8 MB chunks — avoids buffering large files
            f.write(chunk)


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
