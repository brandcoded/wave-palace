"""Public code resolution and follow submission routes (Slice 9)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_code_service, get_follow_service
from app.core.auth import get_current_user
from app.schemas.code import CodePublicResponse
from app.schemas.follow import FollowResponse, FollowSubmitRequest
from app.schemas.user import UserDocument
from app.services.code_service import CodeService
from app.services.follow_service import FollowService

router = APIRouter(prefix="/api/codes", tags=["codes"])


@router.get("/{code}", response_model=CodePublicResponse)
async def resolve_code(
    code: str,
    service: CodeService = Depends(get_code_service),
) -> CodePublicResponse:
    return await service.resolve_code(code)


@router.post("/{code}/follow", response_model=FollowResponse, status_code=201)
async def submit_follow(
    code: str,
    body: FollowSubmitRequest,
    service: FollowService = Depends(get_follow_service),
) -> FollowResponse:
    if body.channel == "sms":
        raise HTTPException(status_code=400, detail="SMS is not available — use Discord or email.")
    frontend_base = os.getenv("FRONTEND_ORIGIN", "https://wavepalace.live").split(",")[0].strip()
    return await service.submit_follow(code, body, frontend_base=frontend_base)


@router.post("/{code}/follow/me", response_model=FollowResponse, status_code=201)
async def follow_as_me(
    code: str,
    user: UserDocument = Depends(get_current_user),
    service: FollowService = Depends(get_follow_service),
) -> FollowResponse:
    """One-click follow for authenticated users — no email confirmation needed."""
    return await service.follow_as_user(code, user)
