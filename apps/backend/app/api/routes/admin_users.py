"""Admin user management routes (Slice 10) — admin-only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_user_repository
from app.core.auth import require_roles
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserDocument, UserPublic, UserRole

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


class RolesUpdate(BaseModel):
    roles: list[UserRole]


class ActiveUpdate(BaseModel):
    is_active: bool


@router.get("", response_model=list[UserPublic])
async def list_users(
    _: UserDocument = Depends(require_roles("admin")),
    repo: UserRepository = Depends(get_user_repository),
) -> list[UserPublic]:
    users = await repo.list_all()
    return [UserPublic(**u.model_dump()) for u in users]


@router.patch("/{user_id}/roles", response_model=UserPublic)
async def update_roles(
    user_id: str,
    body: RolesUpdate,
    _: UserDocument = Depends(require_roles("admin")),
    repo: UserRepository = Depends(get_user_repository),
) -> UserPublic:
    updated = await repo.update(user_id, {"roles": body.roles})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**updated.model_dump())


@router.patch("/{user_id}/active", response_model=UserPublic)
async def update_active(
    user_id: str,
    body: ActiveUpdate,
    _: UserDocument = Depends(require_roles("admin")),
    repo: UserRepository = Depends(get_user_repository),
) -> UserPublic:
    updated = await repo.update(user_id, {"is_active": body.is_active})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**updated.model_dump())
