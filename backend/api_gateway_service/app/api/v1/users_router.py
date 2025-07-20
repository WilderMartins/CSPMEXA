from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.services.http_client import auth_service_client
from app.core.security import require_permission, TokenData

router = APIRouter()

@router.get("/users", name="users:list-users")
async def list_users(
    request: Request,
    current_user: TokenData = Depends(require_permission("read:users"))
):
    """
    Lista todos os usuários. Requer a permissão 'read:users'.
    """
    try:
        response = await auth_service_client.get("/users")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")

@router.post("/users/{user_id}/permissions", name="permissions:add")
async def add_user_permission(
    user_id: int,
    request: Request,
    current_user: TokenData = Depends(require_permission("manage:permissions"))
):
    """
    Adiciona uma permissão a um usuário. Requer a permissão 'manage:permissions'.
    """
    try:
        request_body = await request.json()
        response = await auth_service_client.post(f"/users/{user_id}/permissions", json=request_body)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding user permission: {str(e)}")

@router.delete("/users/{user_id}/permissions", name="permissions:remove")
async def remove_user_permission(
    user_id: int,
    request: Request,
    current_user: TokenData = Depends(require_permission("manage:permissions"))
):
    """
    Remove uma permissão de um usuário. Requer a permissão 'manage:permissions'.
    """
    try:
        request_body = await request.json()
        response = await auth_service_client.delete(f"/users/{user_id}/permissions", json=request_body)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing user permission: {str(e)}")
