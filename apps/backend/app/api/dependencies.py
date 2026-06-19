"""Dependency wiring for the API layer."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.repositories.channel_repository import build_channel_repository
from app.repositories.submission_options_repository import build_submission_options_repository
from app.repositories.submission_repository import build_submission_repository
from app.services.channel_service import ChannelService
from app.services.mux_service import MuxService
from app.services.submission_service import SubmissionService


@lru_cache
def _settings() -> Settings:
    return get_settings()


@lru_cache
def get_channel_service() -> ChannelService:
    repository = build_channel_repository(_settings())
    return ChannelService(repository)


def get_mux_service() -> MuxService:
    from app.repositories.r2_repository import R2Repository

    settings = _settings()
    repository = build_channel_repository(settings)
    r2 = R2Repository(settings)
    return MuxService(repository, r2)


@lru_cache
def get_submission_service() -> SubmissionService:
    settings = _settings()
    submission_repository = build_submission_repository(settings)
    options_repository = build_submission_options_repository(settings)
    return SubmissionService(submission_repository, options_repository)


def get_r2_repository():
    from app.repositories.r2_repository import R2Repository

    return R2Repository(_settings())
