"""Tests for Slice 1C — Audio Visualizer.

Covers:
- Channel schema accepts the new visualizer fields
- ChannelPatchRequest accepts the new fields
- _normalize_taxonomy defaults the new fields for old documents
- _build_image_mux_cmd / _build_video_mux_cmd include the correct
  FFmpeg filter when viz_style is set
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.repositories.channel_repository import _normalize_taxonomy


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_channel_schema_accepts_visualizer_fields():
    from app.schemas.channel import Channel

    ch = Channel(
        id="x",
        slug="test",
        title="Test",
        description="",
        hostName="Host",
        coverImageUrl="https://cdn.test/cover.jpg",
        audioUrl="https://cdn.test/audio.mp3",
        vrchatPlaybackUrl="https://cdn.test/out.mp4",
        visualizer_style="waveform",
        visualizer_theme="teal",
        visualizer_backdrop="replace",
    )
    assert ch.visualizer_style == "waveform"
    assert ch.visualizer_theme == "teal"
    assert ch.visualizer_backdrop == "replace"


def test_channel_schema_defaults():
    from app.schemas.channel import Channel

    ch = Channel(
        id="x",
        slug="test",
        title="Test",
        description="",
        hostName="Host",
        coverImageUrl="https://cdn.test/cover.jpg",
        audioUrl="https://cdn.test/audio.mp3",
        vrchatPlaybackUrl="https://cdn.test/out.mp4",
    )
    assert ch.visualizer_style == "none"
    assert ch.visualizer_theme == "violet"
    assert ch.visualizer_backdrop == "overlay_video"


def test_channel_schema_rejects_invalid_visualizer_style():
    from app.schemas.channel import Channel
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Channel(
            id="x", slug="test", title="Test", description="",
            hostName="Host",
            coverImageUrl="https://cdn.test/cover.jpg",
            audioUrl="https://cdn.test/audio.mp3",
            vrchatPlaybackUrl="https://cdn.test/out.mp4",
            visualizer_style="invalid_style",
        )


# ---------------------------------------------------------------------------
# ChannelPatchRequest
# ---------------------------------------------------------------------------


def test_channel_patch_request_accepts_visualizer_fields():
    from app.api.routes.admin_channels import ChannelPatchRequest

    req = ChannelPatchRequest(
        visualizer_style="bars",
        visualizer_theme="ember",
        visualizer_backdrop="overlay_image",
    )
    assert req.visualizer_style == "bars"
    assert req.visualizer_theme == "ember"
    assert req.visualizer_backdrop == "overlay_image"


def test_visualizer_fields_in_overlay_fields():
    from app.api.routes.admin_channels import _OVERLAY_FIELDS

    assert "visualizer_style" in _OVERLAY_FIELDS
    assert "visualizer_theme" in _OVERLAY_FIELDS
    assert "visualizer_backdrop" in _OVERLAY_FIELDS


# ---------------------------------------------------------------------------
# _normalize_taxonomy
# ---------------------------------------------------------------------------


def test_normalize_taxonomy_defaults_visualizer_fields():
    doc = {"slug": "test", "genre": ["House"], "owner_ids": [], "auto_publish": True}
    normalized = _normalize_taxonomy(doc)
    assert normalized["visualizer_style"] == "none"
    assert normalized["visualizer_theme"] == "violet"
    assert normalized["visualizer_backdrop"] == "overlay_video"


def test_normalize_taxonomy_preserves_existing_visualizer():
    doc = {
        "slug": "test",
        "genre": ["House"],
        "owner_ids": [],
        "auto_publish": True,
        "visualizer_style": "terrain",
        "visualizer_theme": "rose",
        "visualizer_backdrop": "replace",
    }
    normalized = _normalize_taxonomy(doc)
    assert normalized["visualizer_style"] == "terrain"
    assert normalized["visualizer_theme"] == "rose"
    assert normalized["visualizer_backdrop"] == "replace"


# ---------------------------------------------------------------------------
# FFmpeg command builder — image mux
# ---------------------------------------------------------------------------


def test_build_image_mux_cmd_waveform_viz_includes_showwaves():
    from app.services.mux_service import _build_image_mux_cmd

    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="waveform",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "showwaves" in fc
    assert "asplit=2" in fc
    assert "overlay" in fc
    assert "[final_v]" in fc
    assert "[aout_play]" in fc


def test_build_image_mux_cmd_bars_viz_includes_showfreqs():
    from app.services.mux_service import _build_image_mux_cmd

    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="bars",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "showfreqs" in fc


def test_build_image_mux_cmd_circular_viz_includes_avectorscope():
    from app.services.mux_service import _build_image_mux_cmd

    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="circular",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "avectorscope" in fc
    # Circular overlay is centered, not at bottom
    assert "490:210" in fc


def test_build_image_mux_cmd_viz_none_no_asplit():
    from app.services.mux_service import _build_image_mux_cmd

    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="none",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "asplit" not in fc
    assert "[vout]" in fc
    assert "[aout]" in fc


def test_build_image_mux_cmd_viz_with_overlay_combines_both(tmp_path):
    from app.services.mux_service import _build_image_mux_cmd

    font = tmp_path / "DejaVuSans.ttf"
    font.write_bytes(b"fake")
    from app.services.mux_service import _drawtext_overlay

    overlay = _drawtext_overlay("Title", "Host", "Genre", "Mood", str(font))
    cmd = _build_image_mux_cmd(
        Path("/tmp/c.jpg"), [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        overlay=overlay, viz_style="waveform",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "drawtext" in fc
    assert "showwaves" in fc
    assert "[final_v]" in fc


# ---------------------------------------------------------------------------
# FFmpeg command builder — video mux
# ---------------------------------------------------------------------------


def test_build_video_mux_cmd_waveform_viz_includes_showwaves():
    from app.services.mux_service import _build_video_mux_cmd

    cmd = _build_video_mux_cmd(
        Path("/tmp/seg.mp4"), 31, [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="waveform",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "showwaves" in fc
    assert "asplit=2" in fc
    assert "[final_v]" in fc
    # viz-only re-encodes (no stream copy)
    assert cmd[cmd.index("-c:v") + 1] == "libx264"


def test_build_video_mux_cmd_no_viz_stream_copy():
    from app.services.mux_service import _build_video_mux_cmd

    cmd = _build_video_mux_cmd(
        Path("/tmp/seg.mp4"), 31, [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
    )
    assert cmd[cmd.index("-c:v") + 1] == "copy"


def test_build_video_mux_cmd_terrain_bottom_overlay():
    from app.services.mux_service import _build_video_mux_cmd

    cmd = _build_video_mux_cmd(
        Path("/tmp/seg.mp4"), 31, [Path("/tmp/t0.mp3")], Path("/tmp/out.mp4"), 300.0,
        viz_style="terrain",
    )
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "showwaves" in fc
    assert "0:600" in fc  # bottom strip position
