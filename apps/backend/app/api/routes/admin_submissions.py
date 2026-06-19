"""Admin submission review routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_submission_service
from app.core.auth import get_current_admin
from app.models.submission import SubmissionDocument
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api/admin/submissions", tags=["admin-submissions"])

_VALID_STATUSES = {"pending", "approved", "rejected"}


class ReviewRequest(BaseModel):
    status: str
    reviewer_notes: str | None = None


@router.get("", response_model=list[SubmissionDocument])
async def list_submissions(
    status: str = "pending",
    _: dict = Depends(get_current_admin),
    service: SubmissionService = Depends(get_submission_service),
) -> list[SubmissionDocument]:
    if status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{status}'")
    return await service.list_by_status(status)


@router.patch("/{id}", response_model=SubmissionDocument)
async def review_submission(
    id: str,
    body: ReviewRequest,
    _: dict = Depends(get_current_admin),
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionDocument:
    if body.status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{body.status}'")
    result = await service.review(id, body.status, body.reviewer_notes)
    if result is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return result
