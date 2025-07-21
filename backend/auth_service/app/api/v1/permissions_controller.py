from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from app.core.rate_limiter import limiter
from app.services.user_service import user_service
from app.schemas.user_schema import User as UserSchema, PermissionRequest
from app.db.session import get_db
from app.core.security import require_permission

router = APIRouter()

@router.post("/users/{user_id}/permissions", response_model=UserSchema, name="permissions:add")
@limiter.limit("10/minute")
async def add_user_permission(
    request: Request,
    user_id: int,
    permission_request: PermissionRequest,
    db: Session = Depends(get_db),
    admin_user: Session = Depends(require_permission("manage:permissions"))
):
    user_to_update = user_service.get_user_by_id(db, user_id=user_id)
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    updated_user = user_service.add_permission(db, user=user_to_update, permission=permission_request.permission)
    return updated_user

@router.delete("/users/{user_id}/permissions", response_model=UserSchema, name="permissions:remove")
@limiter.limit("10/minute")
async def remove_user_permission(
    request: Request,
    user_id: int,
    permission_request: PermissionRequest,
    db: Session = Depends(get_db),
    admin_user: Session = Depends(require_permission("manage:permissions"))
):
    user_to_update = user_service.get_user_by_id(db, user_id=user_id)
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    updated_user = user_service.remove_permission(db, user=user_to_update, permission=permission_request.permission)
    return updated_user
