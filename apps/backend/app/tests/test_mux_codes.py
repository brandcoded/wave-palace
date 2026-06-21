"""Tests for Slice 9 add-on — deterministic mux codes and flexible matching."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.repositories.code_repository import SeedCodeRepository
from app.repositories.channel_repository import SeedChannelRepository
from app.schemas.code import CodeDocument
from app.services.code_service import (
    CodeService,
    _channel_prefix,
    _track_prefix,
    make_mux_code,
    normalize_code,
)


# ---------------------------------------------------------------------------
# normalize_code — flexible matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("lnh proj",  "LNHPROJ"),
    ("LNH-PROJ",  "LNHPROJ"),
    ("lnh.proj",  "LNHPROJ"),
    ("LNHPROJ",   "LNHPROJ"),
    ("lnhproj",   "LNHPROJ"),
    ("LNH PROJ",  "LNHPROJ"),
])
def test_normalize_code(raw, expected):
    assert normalize_code(raw) == expected


# ---------------------------------------------------------------------------
# _channel_prefix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,expected", [
    ("late-night-house",   "LNH"),
    ("afro-future-lounge", "AFL"),
    ("neon-afterhours",    "NA"),
    ("deep-house",         "DH"),
    ("single",             "S"),
])
def test_channel_prefix(slug, expected):
    assert _channel_prefix(slug) == expected


# ---------------------------------------------------------------------------
# _track_prefix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("title,idx,expected", [
    ("Projections", 3, "PROJ"),
    ("Come Thru",   0, "COME"),
    ("",            2, "T2"),
    ("!!!###",      1, "T1"),
    ("Day Trips",   4, "DAYT"),
    ("Happier",     0, "HAPP"),
])
def test_track_prefix(title, idx, expected):
    assert _track_prefix(title, idx) == expected


# ---------------------------------------------------------------------------
# make_mux_code
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,title,idx,expected", [
    ("late-night-house",   "Projections",   3, "LNHPROJ"),
    ("afro-future-lounge", "Can't Explain", 0, "AFLCANT"),
    ("neon-afterhours",    "Akira",         0, "NAAKIR"),
    ("late-night-house",   "",              2, "LNHT2"),
])
def test_make_mux_code(slug, title, idx, expected):
    assert make_mux_code(slug, title, idx) == expected


# ---------------------------------------------------------------------------
# resolve_code normalizes before lookup
# ---------------------------------------------------------------------------

def _make_stored_code(code: str) -> CodeDocument:
    return CodeDocument(
        code=code,
        channel_slug="late-night-house",
        entity_type="track_channel",
        entity_id="late-night-house",
        track_title="Projections",
        track_artist="DJ Skyy",
        track_index=3,
        source="mux",
        created_at=datetime.now(tz=timezone.utc),
        active=True,
    )


@pytest.mark.parametrize("query", ["lnh proj", "LNH-PROJ", "lnh.proj", "LNHPROJ"])
def test_resolve_normalizes_before_lookup(query):
    code_repo = SeedCodeRepository()
    channel_repo = SeedChannelRepository()
    asyncio.run(code_repo.upsert(_make_stored_code("LNHPROJ")))

    svc = CodeService(code_repo, channel_repo)
    result = asyncio.run(svc.resolve_code(query))
    assert result.code == "LNHPROJ"
    assert result.track_title == "Projections"
    assert result.track_artist == "DJ Skyy"
    assert result.display_name == "Late Night House"


# ---------------------------------------------------------------------------
# upsert_mux_code is idempotent
# ---------------------------------------------------------------------------

def test_upsert_mux_code_idempotent():
    code_repo = SeedCodeRepository()
    channel_repo = SeedChannelRepository()
    svc = CodeService(code_repo, channel_repo)

    asyncio.run(svc.upsert_mux_code("late-night-house", "Projections", "DJ Skyy", 3))
    asyncio.run(svc.upsert_mux_code("late-night-house", "Projections", "DJ Skyy", 3))

    codes = asyncio.run(code_repo.list_all())
    # Should have exactly one code for this track, not two
    lnhproj = [c for c in codes if c.code == "LNHPROJ"]
    assert len(lnhproj) == 1
    assert lnhproj[0].source == "mux"
    assert lnhproj[0].track_index == 3


# ---------------------------------------------------------------------------
# Track info returned in public resolution response
# ---------------------------------------------------------------------------

def test_resolve_returns_track_info():
    code_repo = SeedCodeRepository()
    channel_repo = SeedChannelRepository()
    asyncio.run(code_repo.upsert(_make_stored_code("LNHPROJ")))

    svc = CodeService(code_repo, channel_repo)
    result = asyncio.run(svc.resolve_code("LNHPROJ"))
    assert result.track_title == "Projections"
    assert result.track_artist == "DJ Skyy"


def test_resolve_manual_code_returns_no_track_info():
    """Old random codes have no track fields — response should return None for both."""
    code_repo = SeedCodeRepository()
    channel_repo = SeedChannelRepository()
    doc = CodeDocument(
        code="AB1234",
        channel_slug="late-night-house",
        entity_type="channel",
        entity_id="late-night-house",
        source="manual",
        created_at=datetime.now(tz=timezone.utc),
        active=True,
    )
    asyncio.run(code_repo.create(doc))

    svc = CodeService(code_repo, channel_repo)
    result = asyncio.run(svc.resolve_code("AB1234"))
    assert result.track_title is None
    assert result.track_artist is None
