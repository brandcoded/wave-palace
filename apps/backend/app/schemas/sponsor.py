"""Pydantic schema for the Sponsor domain."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel


class Sponsor(BaseModel):
    name: str
    logoUrl: str | None = None
    text: str = ""
    clickUrl: str | None = None
    placement: str = "lower_third"    # "lower_third" | "bug" | "backdrop"
    startDate: datetime | None = None
    endDate: datetime | None = None
    isActive: bool = True
    isFeatured: bool = False
    impressionCount: int = 0
    clickCount: int = 0


def sponsor_is_live(sponsor: Sponsor | None, now: datetime | None = None) -> bool:
    """Return True when the sponsor exists, is active, and within its date window."""
    if sponsor is None or not sponsor.isActive:
        return False
    t = now or datetime.now(timezone.utc)
    # Normalize to UTC-aware for comparison.
    def _aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    if sponsor.startDate is not None and t < _aware(sponsor.startDate):
        return False
    if sponsor.endDate is not None and t > _aware(sponsor.endDate):
        return False
    return True
