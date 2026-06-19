"""Pydantic schemas for DJ / artist channel submissions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class SubmissionRequest(BaseModel):
    submitter_name: str = Field(..., min_length=1)
    contact_email: EmailStr
    channel_title: str = Field(..., min_length=1)
    profile_image_url: str | None = None
    genre: list[str] = Field(..., min_length=1)
    mood: list[str] = Field(..., min_length=1)
    energy: list[str] = Field(..., min_length=1)
    theme: list[str] = Field(..., min_length=1)
    description: str = Field(..., min_length=20, max_length=500)
    sample_links: list[HttpUrl] = Field(..., min_length=1, max_length=5)
    rights_attestation: bool
    notes: str | None = Field(default=None, max_length=1000)


class SubmissionOptionsResponse(BaseModel):
    genre: list[str]
    mood: list[str]
    energy: list[str]
    theme: list[str]


class ImageUploadResponse(BaseModel):
    url: str


class SubmissionResponse(BaseModel):
    id: str
    status: Literal["pending"]
    submitted_at: datetime
    message: str
