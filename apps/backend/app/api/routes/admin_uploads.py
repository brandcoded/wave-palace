"""Admin media upload routes — image, video, audio → Cloudflare R2."""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from PIL import Image

from app.api.dependencies import get_r2_repository
from app.core.auth import get_current_admin
from app.repositories.r2_repository import R2Repository

router = APIRouter(prefix="/api/admin/upload", tags=["admin-uploads"])

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_VIDEO_TYPES = {"video/mp4"}
_AUDIO_TYPES = {"audio/mpeg", "audio/mp3"}

_IMAGE_MAX_MB = 20
_VIDEO_MAX_MB = 200
_AUDIO_MAX_MB = 1024


def _process_image(data: bytes) -> bytes:
    """Resize to max 1920×1080, convert to WebP, compress if over 500 KB.
    Returns image bytes as WebP. Raises on corrupt image."""
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")

    if img.width > 1920 or img.height > 1080:
        img.thumbnail((1920, 1080), Image.LANCZOS)

    output = io.BytesIO()
    quality = 85
    while quality >= 55:
        output.seek(0)
        output.truncate(0)
        img.save(output, format="WebP", quality=quality)
        if len(output.getvalue()) <= 500 * 1024:
            return output.getvalue()
        quality -= 15

    return output.getvalue()


def _check_type(content_type: str | None, allowed: set[str]) -> None:
    if content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Allowed: {sorted(allowed)}",
        )


def _ext_for(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "video/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
    }
    return mapping.get(content_type, "bin")


async def _upload_stream(
    file: UploadFile,
    r2_key: str,
    content_type: str,
    max_mb: int,
    r2: R2Repository,
) -> str:
    max_bytes = max_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {max_mb} MB limit.",
        )
    return r2.upload_bytes(data, r2_key, content_type)


@router.post("/image")
async def upload_image(
    file: UploadFile,
    _: dict = Depends(get_current_admin),
    r2: R2Repository = Depends(get_r2_repository),
) -> dict:
    _check_type(file.content_type, _IMAGE_TYPES)
    max_bytes = _IMAGE_MAX_MB * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {_IMAGE_MAX_MB} MB limit.",
        )
    processed = _process_image(data)
    r2_key = f"media/images/{uuid.uuid4()}.webp"
    url = r2.upload_bytes(processed, r2_key, "image/webp")
    return {"url": url}


@router.post("/video")
async def upload_video(
    file: UploadFile,
    _: dict = Depends(get_current_admin),
    r2: R2Repository = Depends(get_r2_repository),
) -> dict:
    _check_type(file.content_type, _VIDEO_TYPES)
    r2_key = f"media/videos/{uuid.uuid4()}.mp4"
    url = await _upload_stream(file, r2_key, "video/mp4", _VIDEO_MAX_MB, r2)
    return {"url": url}


@router.post("/audio")
async def upload_audio(
    request: Request,
    file: UploadFile,
    _: dict = Depends(get_current_admin),
    r2: R2Repository = Depends(get_r2_repository),
) -> dict:
    _check_type(file.content_type, _AUDIO_TYPES)
    cl = request.headers.get("content-length")
    if cl and int(cl) > _AUDIO_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {_AUDIO_MAX_MB} MB limit.")
    r2_key = f"media/audio/{uuid.uuid4()}.mp3"
    url = await r2.upload_multipart_stream(file, r2_key, "audio/mpeg")
    return {"url": url}
