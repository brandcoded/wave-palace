"""Mux API routes — internal/admin use only (no auth for MVP).

POST /api/channels/{slug}/mux   — mux a single channel (synchronous, returns URL/error)
POST /api/mux/all               — mux all published channels (background task)

The single-channel endpoint runs synchronously so the caller sees the final
URL or the exact failure. /api/mux/all runs in the background (logs results)
because doing every channel in one request can exceed Render's HTTP timeout.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.dependencies import get_mux_service
from app.services.mux_service import MuxService

router = APIRouter(tags=["mux (internal)"])
logger = logging.getLogger("wavepalace.mux.routes")


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


async def _bg_mux_all(service: MuxService) -> None:
    results = await service.mux_all_published()
    for slug, result in results.items():
        if result.startswith("ERROR:"):
            logger.error("MUX FAILED [%s]: %s", slug, result)
        else:
            logger.info("MUX DONE [%s] -> %s", slug, result)


@router.post("/api/mux/all", status_code=202, summary="Mux all published channels to MP4")
async def mux_all(
    background_tasks: BackgroundTasks,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    background_tasks.add_task(_bg_mux_all, service)
    return {"status": "accepted", "message": "Mux all job started — check Render logs for results."}
