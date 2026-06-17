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

    @property
    def use_seed_mode(self) -> bool:
        """True when no live database is configured."""
        return not self.mongodb_uri


def get_settings() -> Settings:
    return Settings()
