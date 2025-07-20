from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.http_client import audit_service_client
from app.core.security import get_current_user, require_role, TokenData
from app.models.user_model import UserRole

router = APIRouter()

@router.get("/audit/events", name="audit:list-events")
async def list_audit_events(
    request: Request,
    current_user: TokenData = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Lista todos os eventos de auditoria. Requer perfil de Administrador ou Auditor.
    """
    try:
        response = await audit_service_client.get("/events/")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing audit events: {str(e)}")
