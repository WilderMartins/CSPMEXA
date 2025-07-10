from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from app.services.http_client import (
    collector_service_client,
    policy_engine_service_client,
)
from app.core.security import get_current_user, TokenData

# Importar schemas de alerta se precisarmos definir o response_model explicitamente
# from app.schemas.alert_schema import Alert # Supondo que copiamos/referenciamos o schema aqui

router = APIRouter()


@router.post(
    "/analyze/aws/s3", response_model=List[Dict[str, Any]], name="data:analyze_s3"
)  # Usando List[Dict] por enquanto
async def analyze_s3_data_orchestrated(
    request: Request,  # Para repassar headers de autenticação, se necessário
    current_user: TokenData = Depends(get_current_user),  # Protege o endpoint
):
    """
    Orquestra a coleta de dados S3 e sua análise.
    1. Chama o Collector Service para obter dados S3.
    2. Envia os dados S3 para o Policy Engine Service para análise.
    3. Retorna os alertas gerados.
    """
    # Headers para repassar (incluindo o token de autorização)
    # O token já foi validado por get_current_user. Podemos decidir se o repassamos
    # ou se os serviços downstream confiam nas chamadas internas da rede.
    # Para o MVP, vamos assumir que os serviços internos não revalidam o token do usuário final,
    # mas isso pode ser uma consideração de segurança para o futuro (defesa em profundidade).
    # No entanto, os serviços podem ter sua própria autenticação de serviço-a-serviço.
    downstream_headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        downstream_headers["Authorization"] = auth_header

    # 1. Chamar o Collector Service
    s3_collected_data: List[Dict[str, Any]]
    try:
        # O endpoint no collector-service é /api/v1/collect/s3
        collector_response = await collector_service_client.get(
            "/collect/s3", headers=downstream_headers
        )
        if collector_response.status_code != 200:
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service: {collector_response.text}",
            )
        s3_collected_data = collector_response.json()
        if not s3_collected_data:  # Lista vazia, mas não um erro
            return []  # Nenhum dado para analisar, nenhum alerta
        if isinstance(s3_collected_data, list) and s3_collected_data[0].get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Collector Service returned an error: {s3_collected_data[0]['error']}",
            )

    except HTTPException as e:
        # import logging; logging.exception("HTTPException during S3 collection via gateway")
        raise e  # Re-lança a exceção vinda do http_client ou do collector
    except Exception as e:
        # import logging; logging.exception("Error calling Collector Service via gateway")
        raise HTTPException(
            status_code=500, detail=f"Failed to collect S3 data: {str(e)}"
        )

    # 2. Enviar os dados coletados para o Policy Engine Service
    # O Policy Engine espera um corpo JSON como: {"s3_data": [...]}
    analysis_payload = {"s3_data": s3_collected_data}
    alerts: List[Dict[str, Any]]
    try:
        # O endpoint no policy-engine-service é /api/v1/analyze
        engine_response = await policy_engine_service_client.post(
            "/analyze", data=analysis_payload, headers=downstream_headers
        )
        if engine_response.status_code != 200:
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service: {engine_response.text}",
            )
        alerts = engine_response.json()
    except HTTPException as e:
        # import logging; logging.exception("HTTPException during S3 analysis via gateway")
        raise e
    except Exception as e:
        # import logging; logging.exception("Error calling Policy Engine Service via gateway")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze S3 data: {str(e)}"
        )

    # 3. Retornar os alertas
    return alerts


# Adicionar mais endpoints de orquestração para EC2, IAM, etc., conforme os coletores e checkers são desenvolvidos.
# Ex: @router.post("/analyze/aws/ec2", ...)
# Ex: @router.post("/analyze/aws/all", ...) -> orquestraria todos os coletores e análises.
