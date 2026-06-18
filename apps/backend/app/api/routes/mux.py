"""Mux API routes — internal/admin use only (no auth for MVP).

POST /api/channels/{slug}/mux   — mux a single channel (background task)
POST /api/mux/all               — mux all published channels (background task)

Jobs run in the background and log results to stdout. The endpoint returns
202 Accepted immediately so Render's request timeout is never hit.
"""

from __future__ import annotations

import asyncio
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


async def _bg_mux_channel(slug: str, service: MuxService) -> None:
    try:
        url = await service.mux_channel(slug)
        logger.info("MUX DONE [%s] -> %s", slug, url)
    except Exception as exc:
        logger.error("MUX FAILED [%s]: %s", slug, exc)


async def _bg_mux_all(service: MuxService) -> None:
    results = await service.mux_all_published()
    for slug, result in results.items():
        if result.startswith("ERROR:"):
            logger.error("MUX FAILED [%s]: %s", slug, result)
        else:
            logger.info("MUX DONE [%s] -> %s", slug, result)


@router.post("/api/channels/{slug}/mux", status_code=202, summary="Mux a single channel to MP4")
async def mux_channel(
    slug: str,
    background_tasks: BackgroundTasks,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    background_tasks.add_task(_bg_mux_channel, slug, service)
    return {"status": "accepted", "slug": slug, "message": "Mux job started — check Render logs for result."}


@router.post("/api/mux/all", status_code=202, summary="Mux all published channels to MP4")
async def mux_all(
    background_tasks: BackgroundTasks,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    background_tasks.add_task(_bg_mux_all, service)
    return {"status": "accepted", "message": "Mux all job started — check Render logs for results."}
