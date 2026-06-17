"""WavePalace FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import channels, health
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="WavePalace API",
    version="0.1.0",
    description="Visual radio channels for the web and VRChat.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.frontend_origin.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(channels.router)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"service": settings.service_name, "docs": "/docs", "health": "/health"}
