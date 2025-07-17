from fastapi import APIRouter, Depends, HTTPException
from app.services.http_client import policy_engine_service_client
from app.core.security import require_user, TokenData
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/summary", name="dashboard:get_summary")
async def get_dashboard_summary(current_user: TokenData = Depends(require_user)):
    """
    Orquestra a obtenção de dados de resumo para o dashboard.
    """
    try:
        # Chamar o endpoint de sumário do policy_engine_service
        response = await policy_engine_service_client.get("/alerts/summary")
        response.raise_for_status()  # Levanta uma exceção para status de erro HTTP

        summary_data = response.json()

        # Aqui podemos enriquecer os dados com informações de outros serviços no futuro

        return summary_data

    except HTTPException as e:
        # Re-lançar exceções HTTP para que o FastAPI as manipule
        raise e
    except Exception as e:
        logger.exception("Erro ao buscar dados de sumário para o dashboard.")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar dados para o dashboard.")
