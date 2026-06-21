"""Admin code management routes (Slice 9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_code_service
from app.core.auth import get_current_admin
from app.schemas.code import CodeCreateRequest, CodeDocument
from app.services.code_service import CodeService

router = APIRouter(prefix="/api/admin/codes", tags=["admin-codes"])


@router.post("", response_model=CodeDocument, status_code=201)
async def create_code(
    body: CodeCreateRequest,
    _: dict = Depends(get_current_admin),
    service: CodeService = Depends(get_code_service),
) -> CodeDocument:
    return await service.generate_code(body)


@router.get("", response_model=list[CodeDocument])
async def list_codes(
    _: dict = Depends(get_current_admin),
    service: CodeService = Depends(get_code_service),
) -> list[CodeDocument]:
    return await service.list_codes()


@router.delete("/{code}")
async def deactivate_code(
    code: str,
    _: dict = Depends(get_current_admin),
    service: CodeService = Depends(get_code_service),
) -> Response:
    await service.deactivate_code(code)
    return Response(status_code=204)
