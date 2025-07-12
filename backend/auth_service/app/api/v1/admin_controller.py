from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any
from app.services.credentials_service import credentials_service
from app.schemas.credentials_schema import StoredCredentialInfo, AWSCredentials, AzureCredentials
# Importar a dependência de segurança quando for criada
# from app.core.security import get_current_active_admin_user

router = APIRouter()

# Placeholder para a dependência de admin. Por enquanto, não vamos proteger o endpoint.
# Em um commit futuro, substituiríamos `Depends()` por `Depends(get_current_active_admin_user)`.
def get_admin_user_placeholder():
    # Esta função não faz nada e será substituída por uma verificação de admin real.
    pass

@router.post("/credentials/{provider}", status_code=204, summary="Salvar Credenciais de um Provedor")
async def save_provider_credentials(
    provider: str,
    credentials: Dict[str, Any] = Body(...),
    # current_admin: User = Depends(get_admin_user_placeholder) # Ativar quando a segurança estiver pronta
):
    """
    Salva ou atualiza as credenciais para um determinado provedor de nuvem.
    - **provider**: O nome do provedor (ex: 'aws', 'azure').
    - **credentials**: Um objeto JSON com as credenciais.
    """
    try:
        # Aqui poderíamos validar o corpo das credenciais com base no provedor
        # Ex: if provider == 'aws': AWSCredentials(**credentials)
        credentials_service.save_credentials(provider=provider, credentials=credentials)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar credenciais: {e}")
    return

@router.get("/credentials", response_model=List[StoredCredentialInfo], summary="Listar Provedores Configurados")
async def list_configured_providers(
    # current_admin: User = Depends(get_admin_user_placeholder) # Ativar quando a segurança estiver pronta
):
    """
    Retorna uma lista de todos os provedores de nuvem que têm credenciais configuradas no sistema.
    """
    try:
        return credentials_service.get_configured_providers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar provedores: {e}")

@router.delete("/credentials/{provider}", status_code=204, summary="Deletar Credenciais de um Provedor")
async def delete_provider_credentials(
    provider: str,
    # current_admin: User = Depends(get_admin_user_placeholder) # Ativar quando a segurança estiver pronta
):
    """
    Remove permanentemente as credenciais de um provedor do sistema.
    """
    try:
        credentials_service.delete_credentials(provider=provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar credenciais: {e}")
    return
