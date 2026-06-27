"""Application configuration loaded from environment variables.

The MVP is designed to run locally with no external services. If MONGODB_URI
is not provided, the app falls back to in-memory seed data (seed mode).
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    service_name: str = "wavepalace-api"
    mongodb_uri: Optional[str] = os.getenv("MONGODB_URI") or None
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "wavepalace")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000,http://localhost:3001")

    # Cloudflare R2 (S3-compatible) — used by the mux service to upload MP4s.
    r2_account_id: Optional[str] = os.getenv("R2_ACCOUNT_ID") or None
    r2_access_key_id: Optional[str] = os.getenv("R2_ACCESS_KEY_ID") or None
    r2_secret_access_key: Optional[str] = os.getenv("R2_SECRET_ACCESS_KEY") or None
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "wavepalace-media")
    r2_public_base_url: str = os.getenv("R2_PUBLIC_BASE_URL", "https://stream.wavepalace.live")

    # Admin dashboard auth — single-secret bootstrap + Slice 10 opaque sessions.
    admin_secret: str = os.getenv("ADMIN_SECRET", "changeme")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")
    session_ttl_days: int = int(os.getenv("SESSION_TTL_DAYS", "30"))

    # Slice 9 — Code Capture + Follow Intent + Notifications
    discord_bot_token: Optional[str] = os.getenv("DISCORD_BOT_TOKEN") or None
    discord_client_id: Optional[str] = os.getenv("DISCORD_CLIENT_ID") or None
    discord_client_secret: Optional[str] = os.getenv("DISCORD_CLIENT_SECRET") or None
    discord_redirect_uri: Optional[str] = os.getenv("DISCORD_REDIRECT_URI") or None
    # ID of the WavePalace Discord server. When set the bot auto-adds followers
    # so DMs always succeed (requires the bot to have Create Instant Invite in that server).
    discord_guild_id: Optional[str] = os.getenv("DISCORD_GUILD_ID") or None
    vapid_public_key: Optional[str] = os.getenv("VAPID_PUBLIC_KEY") or None
    vapid_private_key: Optional[str] = os.getenv("VAPID_PRIVATE_KEY") or None
    resend_api_key: Optional[str] = os.getenv("RESEND_API_KEY") or None

    # DMCA takedown email notification — all optional; email skips silently if absent.
    admin_email: Optional[str] = os.getenv("ADMIN_EMAIL") or None
    smtp_host: Optional[str] = os.getenv("SMTP_HOST") or None
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: Optional[str] = os.getenv("SMTP_USER") or None
    smtp_pass: Optional[str] = os.getenv("SMTP_PASS") or None

    # Path to a TrueType font used by the mux service to burn text overlays
    # into VRChat MP4s. Defaults to DejaVu Sans on Ubuntu (installed via apt
    # in render.yaml). Override with FONT_PATH env var for other environments.
    font_path: str = os.getenv(
        "FONT_PATH",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )

    @property
    def use_seed_mode(self) -> bool:
        """True when no live database is configured."""
        return not self.mongodb_uri

    @property
    def r2_configured(self) -> bool:
        """True when all R2 credentials are present."""
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key)

    @property
    def r2_endpoint_url(self) -> str:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


def get_settings() -> Settings:
    return Settings()
