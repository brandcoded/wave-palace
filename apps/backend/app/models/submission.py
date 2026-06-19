"""MongoDB document model for DJ / artist submissions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class SubmissionDocument(BaseModel):
    id: str
    submitter_name: str
    contact_email: str
    channel_title: str
    profile_image_url: str | None = None
    genre: list[str]
    mood: list[str]
    energy: list[str]
    theme: list[str]
    description: str
    sample_links: list[HttpUrl]
    rights_attestation: bool
    notes: str | None = None
    status: str = "pending"
    submitted_at: datetime
    reviewed_at: datetime | None = None
    reviewer_notes: str | None = None

    model_config = {"populate_by_name": True}


class SubmissionOptionsDocument(BaseModel):
    field: str
    options: list[str]
    updated_at: datetime = Field(default_factory=datetime.utcnow)
