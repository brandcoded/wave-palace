"""Dependency wiring for the API layer."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.repositories.channel_repository import build_channel_repository
from app.services.channel_service import ChannelService


@lru_cache
def _settings() -> Settings:
    return get_settings()


@lru_cache
def get_channel_service() -> ChannelService:
    repository = build_channel_repository(_settings())
    return ChannelService(repository)
