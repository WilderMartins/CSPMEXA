from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.http_client import collector_service_client
from app.core.security import require_permission, TokenData

require_remediate_s3 = require_permission("remediate:s3")

router = APIRouter()

@router.post("/remediate/aws/s3/public-acl", name="remediate:aws-s3-public-acl")
async def remediate_s3_public_acl(
    request: Request,
    current_user: TokenData = Depends(require_remediate_s3)
):
    """
    Aciona a remediação para um bucket S3 com ACL pública.
    Requer perfil de Administrador ou Analista.
    """
    try:
        request_body = await request.json()
        response = await collector_service_client.post("/remediate/aws/s3/public-acl", json=request_body)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering S3 public ACL remediation: {str(e)}")
