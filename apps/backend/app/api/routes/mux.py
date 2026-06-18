"""Mux API routes — internal/admin use only (no auth for MVP).

POST /api/channels/{slug}/mux   — mux a single channel (synchronous, returns URL/error)
POST /api/mux/all               — start a background job muxing every published channel
GET  /api/mux/status            — poll the status of the most recent /api/mux/all job

On Render's CPU-throttled free tier a single channel can take ~25s+ and a
synchronous "mux everything" request exceeds the platform's HTTP timeout
(observed as a 502). So /api/mux/all runs in the background and records
per-channel progress in an in-memory store that GET /api/mux/status returns.
Poll that endpoint until every channel reports "done" or "error".
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.dependencies import get_mux_service
from app.services.mux_service import MuxService

router = APIRouter(tags=["mux (internal)"])
logger = logging.getLogger("wavepalace.mux.routes")

# Bump when the mux pipeline changes; surfaced by GET /api/mux/status.
MUX_BUILD = "videoloop-v4"

# In-memory status of the most recent /api/mux/all run. Single Render instance
# / single uvicorn worker, so a module-level dict is sufficient for this
# admin-only tool. Reset each time a new /api/mux/all job starts.
_JOB: dict = {"running": False, "started_at": None, "finished_at": None, "channels": {}}


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


async def _run_mux_all(service: MuxService) -> None:
    slugs = await service.published_slugs()
    _JOB["channels"] = {s: {"state": "pending", "url": None, "error": None} for s in slugs}
    for slug in slugs:
        _JOB["channels"][slug]["state"] = "running"
        try:
            url = await service.mux_channel(slug)
            _JOB["channels"][slug].update(state="done", url=url)
            logger.info("MUX DONE [%s] -> %s", slug, url)
        except Exception as exc:  # noqa: BLE001
            _JOB["channels"][slug].update(state="error", error=str(exc))
            logger.error("MUX FAILED [%s]: %s", slug, exc)
    _JOB["running"] = False
    _JOB["finished_at"] = time.time()


@router.post("/api/mux/all", status_code=202, summary="Start background mux of all channels")
async def mux_all(
    background_tasks: BackgroundTasks,
    service: MuxService = Depends(get_mux_service),
) -> dict:
    if _JOB["running"]:
        raise HTTPException(status_code=409, detail="A mux job is already running. Poll /api/mux/status.")
    _JOB.update(running=True, started_at=time.time(), finished_at=None, channels={})
    background_tasks.add_task(_run_mux_all, service)
    return {"status": "accepted", "poll": "/api/mux/status"}


@router.get("/api/mux/status", summary="Status of the most recent mux-all job")
async def mux_status() -> dict:
    return {"build": MUX_BUILD, **_JOB}
