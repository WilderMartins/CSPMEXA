from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Any
from app.schemas.input_data_schema import AnalysisRequest
# Os schemas específicos como S3BucketDataInput já são usados pelo AnalysisRequest com o Union (SupportedDataTypes)
from app.schemas.alert_schema import Alert
from app.engine.core_engine import policy_engine # Importa a instância do PolicyEngine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# TODO: Adicionar autenticação de serviço-para-serviço para este endpoint se necessário.
# Por enquanto, ele está aberto dentro da rede interna, mas o gateway pode proteger o acesso externo.

@router.post("/analyze", response_model=List[Alert])
async def analyze_resources(
    analysis_request: AnalysisRequest = Body(...) # Pydantic validará o tipo de 'data' com base no 'service' via Union
):
    """
    Endpoint para analisar dados de configuração de recursos e retornar alertas.
    Recebe um AnalysisRequest com 'provider', 'service', e 'data' correspondente.
    O campo 'data' do AnalysisRequest deve ser uma lista de objetos que correspondem
    ao 'service' especificado (e.g., List[S3BucketDataInput] se service='s3').
    """

    # Log da requisição recebida (cuidado com dados sensíveis em produção se 'data' for logado)
    logger.info(f"Received analysis request for provider: {analysis_request.provider}, service: {analysis_request.service}, account: {analysis_request.account_id or 'N/A'}")
    # logger.debug(f"Data for analysis: {analysis_request.data}") # Pode ser muito verboso e sensível

    if not analysis_request.data:
        logger.info(f"No data provided in analysis request for service: {analysis_request.service}. Returning empty list.")
        return []

    # O Pydantic, ao validar AnalysisRequest, já tentou converter 'data' para um dos tipos
    # em SupportedDataTypes. Se a conversão falhou (ex: 'service' é 's3' mas 'data' não é
    # uma lista de S3BucketDataInput válidos), um erro de validação 422 já teria sido retornado.
    # Portanto, aqui podemos confiar que 'data' tem o tipo esperado pelo 'service'.

    try:
        alerts = policy_engine.analyze(analysis_request)
        logger.info(f"Analysis for {analysis_request.provider}/{analysis_request.service} (Account: {analysis_request.account_id or 'N/A'}) completed. Found {len(alerts)} alerts.")
        return alerts
    except Exception as e:
        logger.exception(f"Error during resource analysis for service {analysis_request.service}")
        # O core_engine.analyze pode levantar exceções específicas que podem ser tratadas aqui
        # ou simplesmente capturar tudo e retornar um erro 500.
        raise HTTPException(
            status_code=500, detail=f"Error during resource analysis for {analysis_request.service}: {str(e)}"
        )
