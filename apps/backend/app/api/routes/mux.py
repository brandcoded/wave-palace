"""Mux API routes — internal/admin use only (no auth for MVP).

POST /api/channels/{slug}/mux   — mux a single channel
POST /api/mux/all               — mux all published channels

These endpoints download cover art + audio from R2, run FFmpeg to produce
a VRChat-compatible MP4, upload the result back to R2, and return the URL.
They require R2 credentials to be set via environment variables.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_mux_service
from app.services.mux_service import MuxService

router = APIRouter(tags=["mux (internal)"])


@router.get("/api/mux/debug", summary="Debug R2 config (temporary)")
async def mux_debug() -> dict:
    import os
    return {
        "R2_ACCOUNT_ID": (os.getenv("R2_ACCOUNT_ID") or "")[:6] + "...",
        "R2_ACCESS_KEY_ID": (os.getenv("R2_ACCESS_KEY_ID") or "")[:6] + "...",
        "R2_SECRET_ACCESS_KEY_set": bool(os.getenv("R2_SECRET_ACCESS_KEY")),
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME"),
        "R2_PUBLIC_BASE_URL": os.getenv("R2_PUBLIC_BASE_URL"),
    }


@router.post("/api/channels/{slug}/mux", summary="Mux a single channel to MP4")
async def mux_channel(
    slug: str,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    try:
        url = await service.mux_channel(slug)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"slug": slug, "vrchatPlaybackUrl": url}


@router.post("/api/mux/all", summary="Mux all published channels to MP4")
async def mux_all(
    service: MuxService = Depends(get_mux_service),
) -> dict:
    try:
        results = await service.mux_all_published()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"results": results}
