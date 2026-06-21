"""DMCA / Copyright Takedown routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.dependencies import get_takedown_service
from app.schemas.takedown import (
    TakedownDocument,
    TakedownStatusUpdate,
    TakedownSubmitRequest,
    TakedownSubmitResponse,
)
from app.services.takedown_service import TakedownService

router = APIRouter(prefix="/api/takedowns", tags=["takedowns"])


@router.post("", response_model=TakedownSubmitResponse, status_code=201)
async def submit_takedown(
    body: TakedownSubmitRequest,
    service: TakedownService = Depends(get_takedown_service),
) -> TakedownSubmitResponse:
    return await service.submit(body)


@router.get("", response_model=list[TakedownDocument])
async def list_takedowns(
    service: TakedownService = Depends(get_takedown_service),
) -> list[TakedownDocument]:
    return await service.list_all()


@router.get("/{takedown_id}", response_model=TakedownDocument)
async def get_takedown(
    takedown_id: str,
    service: TakedownService = Depends(get_takedown_service),
) -> TakedownDocument:
    doc = await service.get(takedown_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Takedown request not found")
    return doc


@router.patch("/{takedown_id}/status", response_model=TakedownDocument)
async def update_takedown_status(
    takedown_id: str,
    body: TakedownStatusUpdate,
    service: TakedownService = Depends(get_takedown_service),
) -> TakedownDocument:
    doc = await service.update_status(takedown_id, body)
    if not doc:
        raise HTTPException(status_code=404, detail="Takedown request not found")
    return doc
