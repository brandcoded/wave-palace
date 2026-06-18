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
