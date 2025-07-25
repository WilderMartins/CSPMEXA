from typing import Dict, Any, Optional
from app.services.http_client import auth_service_client
import logging

logger = logging.getLogger(__name__)

async def get_credentials_for_account(linked_account_id: int, auth_token: str) -> Optional[Dict[str, Any]]:
    """
    Busca as credenciais de uma conta específica do auth_service.
    Requer o token JWT do usuário para autorização.
    """
    if not auth_token:
        logger.warning("Nenhum token de autenticação fornecido para buscar credenciais.")
        return None

    headers = {"Authorization": auth_token}
    try:
        # O auth_service precisa de um endpoint para fornecer as credenciais
        # para uma conta específica. Vamos supor que seja /internal/credentials/{id}
        # e que seja protegido.
        response = await auth_service_client.get(
            f"/accounts/{linked_account_id}/credentials", headers=headers
        )
        await response.raise_for_status()
        return await response.json()
    except Exception as e:
        logger.error(f"Erro ao buscar credenciais para a conta ID {linked_account_id}: {e}")
        return None
