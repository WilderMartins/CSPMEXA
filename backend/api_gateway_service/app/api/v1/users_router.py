from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.services.http_client import auth_service_client
from app.core.security import get_current_user, require_role, TokenData
from app.models.user_model import UserRole

router = APIRouter()

@router.get("/users", name="users:list-users")
async def list_users(
    request: Request,
    current_user: TokenData = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST]))
):
    """
    Lista todos os usuários. Requer perfil de Administrador ou Analista.
    """
    try:
        response = await auth_service_client.get("/users")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")

@router.put("/users/{user_id}/role", name="users:update-role")
async def update_user_role(
    user_id: int,
    request: Request,
    current_user: TokenData = Depends(require_role([UserRole.ADMIN]))
):
    """
    Atualiza o perfil de um usuário. Requer perfil de Administrador.
    """
    try:
        request_body = await request.json()
        response = await auth_service_client.put(f"/users/{user_id}/role", json=request_body)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user role: {str(e)}")
