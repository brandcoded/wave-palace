"""Business rules for public DJ / artist submissions."""

from __future__ import annotations

from fastapi import HTTPException

from app.models.submission import SubmissionDocument
from app.repositories.submission_options_repository import SubmissionOptionsRepository
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.submission import SubmissionOptionsResponse, SubmissionRequest, SubmissionResponse


class SubmissionService:
    def __init__(
        self,
        submission_repository: SubmissionRepository,
        options_repository: SubmissionOptionsRepository,
    ) -> None:
        self._submission_repository = submission_repository
        self._options_repository = options_repository

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def get_options(self) -> SubmissionOptionsResponse:
        return SubmissionOptionsResponse.model_validate(await self._options_repository.get_all())

    async def submit(self, data: SubmissionRequest) -> SubmissionResponse:
        if not data.rights_attestation:
            raise HTTPException(status_code=422, detail="Rights attestation required")

        options = await self._options_repository.get_all()
        for field in ("genre", "mood", "energy", "theme"):
            allowed = set(options[field])
            for value in getattr(data, field):
                if value not in allowed:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid {field} value: {value}",
                    )

        document = await self._submission_repository.create(data)
        return SubmissionResponse(
            id=document.id,
            status="pending",
            submitted_at=document.submitted_at,
            message=(
                f"Thanks {data.submitter_name} — your submission is in review. "
                f"We'll be in touch at {data.contact_email}."
            ),
        )

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    async def list_by_status(self, status: str) -> list[SubmissionDocument]:
        return await self._submission_repository.list_by_status(status)

    async def review(
        self, id: str, status: str, reviewer_notes: str | None
    ) -> SubmissionDocument | None:
        return await self._submission_repository.update_review(id, status, reviewer_notes)

    async def get_submission_options(self) -> dict:
        return await self._options_repository.get_all()

    async def update_submission_options(self, field: str, options: list[str]) -> None:
        await self._options_repository.upsert(field, options)
