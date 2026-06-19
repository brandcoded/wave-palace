"""Public submission routes for DJ / artist channel proposals."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_r2_repository, get_submission_service
from app.repositories.r2_repository import R2Repository
from app.schemas.submission import (
    ImageUploadResponse,
    SubmissionOptionsResponse,
    SubmissionRequest,
    SubmissionResponse,
)
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api", tags=["submissions"])

_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_UPLOAD_LIMIT = 10
_SUBMIT_LIMIT = 3
_WINDOW_SECONDS = 60 * 60
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str, limit: int) -> None:
    now = time.time()
    bucket = _RATE_BUCKETS[key]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)


@router.get(
    "/submission-options",
    response_model=SubmissionOptionsResponse,
)
async def get_submission_options(
    service: SubmissionService = Depends(get_submission_service),
) -> JSONResponse:
    options = await service.get_options()
    return JSONResponse(
        content=options.model_dump(),
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post(
    "/submissions/upload-image",
    response_model=ImageUploadResponse,
)
async def upload_submission_image(
    request: Request,
    file: UploadFile,
    r2: R2Repository = Depends(get_r2_repository),
) -> ImageUploadResponse:
    _check_rate_limit(f"upload:{_client_ip(request)}", _UPLOAD_LIMIT)

    content_type = file.content_type or ""
    extension = _ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")

    key = f"submissions/images/{uuid4()}.{extension}"
    url = r2.upload_bytes(data, key, content_type)
    return ImageUploadResponse(url=url)


@router.post(
    "/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_proposal(
    request: Request,
    data: SubmissionRequest,
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionResponse:
    _check_rate_limit(f"submit:{_client_ip(request)}", _SUBMIT_LIMIT)
    return await service.submit(data)


def reset_rate_limits() -> None:
    """Test helper to clear in-memory rate buckets."""
    _RATE_BUCKETS.clear()
