"""WavePalace FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import channels, health, mux, submissions
from app.api.routes import admin_auth, admin_channels, admin_submissions, admin_uploads, admin_options
from app.api.routes import codes, follows, auth_discord, admin_codes
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

# Public routes
app.include_router(health.router)
app.include_router(channels.router)
app.include_router(mux.router)
app.include_router(submissions.router)

# Admin routes
app.include_router(admin_auth.router)
app.include_router(admin_channels.router)
app.include_router(admin_submissions.router)
app.include_router(admin_uploads.router)
app.include_router(admin_options.router)
app.include_router(admin_codes.router)

# Slice 9 — Code Capture + Follow Intent
app.include_router(codes.router)
app.include_router(follows.router)
app.include_router(auth_discord.router)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"service": settings.service_name, "docs": "/docs", "health": "/health"}
