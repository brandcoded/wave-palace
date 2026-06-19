"""Admin submission options management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_submission_service
from app.core.auth import get_current_admin
from app.repositories.submission_options_repository import OPTION_FIELDS
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api/admin/options", tags=["admin-options"])

_VALID_FIELDS = set(OPTION_FIELDS)


class OptionsUpdateRequest(BaseModel):
    options: list[str]


@router.get("")
async def get_options(
    _: dict = Depends(get_current_admin),
    service: SubmissionService = Depends(get_submission_service),
) -> dict:
    return await service.get_submission_options()


@router.patch("/{field}")
async def update_options(
    field: str,
    body: OptionsUpdateRequest,
    _: dict = Depends(get_current_admin),
    service: SubmissionService = Depends(get_submission_service),
) -> dict:
    if field not in _VALID_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid field '{field}'. Must be one of: {sorted(_VALID_FIELDS)}",
        )
    cleaned = [o.strip() for o in body.options if o.strip()]
    if not cleaned:
        raise HTTPException(status_code=422, detail="options must be a non-empty list of strings")
    await service.update_submission_options(field, cleaned)
    return {"field": field, "options": cleaned}
