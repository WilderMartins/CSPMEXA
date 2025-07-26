from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.http_client import policy_engine_service_client as audit_service_client
from app.core.security import require_permission, TokenData

require_read_audit = require_permission("read:audit")

router = APIRouter()

@router.get("/audit/events", name="audit:list-events")
async def list_audit_events(
    request: Request,
    current_user: TokenData = Depends(require_read_audit),
):
    """
    Lista todos os eventos de auditoria. Requer perfil de Administrador ou Auditor.
    """
    try:
        response = await audit_service_client.get("/events/")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing audit events: {str(e)}")
