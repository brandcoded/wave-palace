"""Dependency wiring for the API layer."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.repositories.channel_repository import ChannelRepository, build_channel_repository
from app.repositories.submission_options_repository import build_submission_options_repository
from app.repositories.submission_repository import build_submission_repository
from app.services.channel_service import ChannelService
from app.services.mux_service import MuxService
from app.services.submission_service import SubmissionService


@lru_cache
def _settings() -> Settings:
    return get_settings()


@lru_cache
def get_channel_repository() -> ChannelRepository:
    """Single shared channel repository.

    Must be a singleton: in seed mode the repository holds the only copy of the
    channel data in memory, so every service (channel + mux) has to read and
    write the SAME instance. Building a fresh repository per service would make
    writes from one service (e.g. the mux clearing muxOutdated) invisible to the
    others, leaving stale state.
    """
    return build_channel_repository(_settings())


@lru_cache
def get_channel_service() -> ChannelService:
    return ChannelService(get_channel_repository())


@lru_cache
def get_mux_service() -> MuxService:
    from app.repositories.r2_repository import R2Repository

    return MuxService(get_channel_repository(), R2Repository(_settings()))


@lru_cache
def get_submission_service() -> SubmissionService:
    settings = _settings()
    submission_repository = build_submission_repository(settings)
    options_repository = build_submission_options_repository(settings)
    return SubmissionService(submission_repository, options_repository)


def get_r2_repository():
    from app.repositories.r2_repository import R2Repository

    return R2Repository(_settings())


@lru_cache
def get_code_repository():
    from app.repositories.code_repository import build_code_repository
    return build_code_repository(_settings())


@lru_cache
def get_follow_repository():
    from app.repositories.follow_repository import build_follow_repository
    return build_follow_repository(_settings())


@lru_cache
def get_code_service():
    from app.services.code_service import CodeService
    return CodeService(get_code_repository(), get_channel_repository())


@lru_cache
def get_follow_service():
    from app.services.follow_service import FollowService
    return FollowService(get_follow_repository(), get_code_repository(), get_channel_repository())
