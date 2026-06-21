"""Schemas for the DMCA / Copyright Takedown slice."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


TakedownStatus = Literal["pending", "reviewed", "actioned", "dismissed"]
TakedownRole = Literal["artist", "label", "attorney", "other"]


class TakedownDocument(BaseModel):
    id: str
    claimant_name: str
    organization: Optional[str] = None
    email: str
    role: TakedownRole
    infringing_url: str
    description: str
    proof: Optional[str] = None
    good_faith: bool
    accuracy: bool
    status: TakedownStatus = "pending"
    submitted_at: datetime
    notes: Optional[str] = None


class TakedownSubmitRequest(BaseModel):
    claimant_name: str
    organization: Optional[str] = None
    email: str
    role: TakedownRole
    infringing_url: str
    description: str
    proof: Optional[str] = None
    good_faith: bool
    accuracy: bool

    @field_validator("good_faith")
    @classmethod
    def good_faith_must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Good-faith statement is required")
        return v

    @field_validator("accuracy")
    @classmethod
    def accuracy_must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Accuracy statement is required")
        return v


class TakedownSubmitResponse(BaseModel):
    id: str
    submitted_at: datetime


class TakedownStatusUpdate(BaseModel):
    status: TakedownStatus
    notes: Optional[str] = None
