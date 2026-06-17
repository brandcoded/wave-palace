"""Pytest fixtures: a TestClient wired to the seed repository."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_channel_service
from app.main import app
from app.repositories.channel_repository import SeedChannelRepository
from app.services.channel_service import ChannelService


@pytest.fixture()
def client() -> TestClient:
    # Force seed mode for deterministic tests regardless of environment.
    service = ChannelService(SeedChannelRepository())
    app.dependency_overrides[get_channel_service] = lambda: service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
