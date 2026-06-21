"""Code generation and resolution for Slice 9."""

from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories.channel_repository import ChannelRepository
from app.repositories.code_repository import CodeRepository
from app.schemas.code import CodeCreateRequest, CodeDocument, CodePublicResponse

_ALPHABET = string.ascii_uppercase + string.digits


def _random_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


def normalize_code(raw: str) -> str:
    """Strip separators and uppercase — 'lnh proj', 'LNH-PROJ', 'lnh.proj' → 'LNHPROJ'."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def _channel_prefix(channel_slug: str) -> str:
    """late-night-house → LNH (first letter of each hyphen-word, max 4)."""
    words = channel_slug.replace("-", " ").split()
    return "".join(w[0].upper() for w in words if w)[:4]


def _track_prefix(track_title: str, track_index: int) -> str:
    """Projections → PROJ (first 4 uppercase alphanum chars). Falls back to T{index}."""
    clean = re.sub(r"[^A-Z0-9]", "", track_title.upper())
    return clean[:4] if clean else f"T{track_index}"


def make_mux_code(channel_slug: str, track_title: str, track_index: int) -> str:
    """Deterministic mux code: channel prefix + track prefix. e.g. 'LNHPROJ'."""
    return _channel_prefix(channel_slug) + _track_prefix(track_title, track_index)


class CodeService:
    def __init__(self, code_repo: CodeRepository, channel_repo: ChannelRepository) -> None:
        self._code_repo = code_repo
        self._channel_repo = channel_repo

    async def generate_code(self, request: CodeCreateRequest) -> CodeDocument:
        for _ in range(5):
            candidate = _random_code()
            if not await self._code_repo.code_exists_active(candidate):
                doc = CodeDocument(
                    code=candidate,
                    channel_slug=request.channel_slug,
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    created_at=datetime.now(tz=timezone.utc),
                    expires_at=request.expires_at,
                    active=True,
                )
                return await self._code_repo.create(doc)
        raise HTTPException(status_code=409, detail="Could not generate a unique code — try again.")

    async def resolve_code(self, code: str) -> CodePublicResponse:
        doc = await self._code_repo.get(normalize_code(code))
        if doc is None or not doc.active:
            raise HTTPException(
                status_code=404,
                detail="This code is no longer active — tune in at wavepalace.live",
            )
        now = datetime.now(tz=timezone.utc)
        if doc.expires_at:
            exp = doc.expires_at
            if exp.tzinfo is None:
                from datetime import timezone as tz
                exp = exp.replace(tzinfo=tz.utc)
            if exp < now:
                raise HTTPException(
                    status_code=404,
                    detail="This code is no longer active — tune in at wavepalace.live",
                )
        channel = await self._channel_repo.get_by_slug(doc.channel_slug)
        display_name = channel.get("title", doc.channel_slug) if channel else doc.channel_slug
        host_name = channel.get("hostName") if channel else None
        genre = channel.get("genre") if channel else None
        mood = channel.get("mood") if channel else None
        cover_image_url = channel.get("coverImageUrl") if channel else None
        return CodePublicResponse(
            code=doc.code,
            entity_type=doc.entity_type,
            entity_id=doc.entity_id,
            display_name=display_name,
            host_name=host_name,
            genre=genre,
            mood=mood,
            cover_image_url=str(cover_image_url) if cover_image_url else None,
            track_title=doc.track_title,
            track_artist=doc.track_artist,
        )

    async def upsert_mux_code(
        self,
        channel_slug: str,
        track_title: str,
        track_artist: str,
        track_index: int,
    ) -> CodeDocument:
        """Generate deterministic mux code and upsert. Idempotent on re-mux."""
        code = make_mux_code(channel_slug, track_title, track_index)
        doc = CodeDocument(
            code=code,
            channel_slug=channel_slug,
            entity_type="track_channel",
            entity_id=channel_slug,
            track_title=track_title,
            track_artist=track_artist,
            track_index=track_index,
            source="mux",
            created_at=datetime.now(tz=timezone.utc),
            active=True,
        )
        return await self._code_repo.upsert(doc)

    async def deactivate_code(self, code: str) -> None:
        found = await self._code_repo.deactivate(code.upper())
        if not found:
            raise HTTPException(status_code=404, detail="Code not found")

    async def list_codes(self) -> list[CodeDocument]:
        return await self._code_repo.list_all()
