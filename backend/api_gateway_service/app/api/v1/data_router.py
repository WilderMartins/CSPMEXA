from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Dict, Any, Optional
from app.services.http_client import (
    collector_service_client,
    policy_engine_service_client,
)
from app.core.security import get_current_user, TokenData

# Importar os schemas copiados/criados para o gateway
from app.schemas import collector_s3_schemas, collector_ec2_schemas, collector_iam_schemas, policy_engine_alert_schema

import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Endpoints de Coleta (Proxy para Collector Service) ---
# O tipo de retorno de _proxy_collector_request é Any,
# mas os endpoints específicos terão response_model mais concreto.

async def _proxy_collector_request(
    method: str,
    collector_endpoint: str,
    current_user: TokenData, # Para garantir que o endpoint é protegido
    request: Request, # Para potencialmente extrair headers, se necessário no futuro
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None, # Mudado para Dict para consistência com POST JSON
) -> Any:
    """Função helper para fazer proxy de chamadas GET/POST para o collector_service."""
    # Headers para serviços downstream. Atualmente, o collector-service não valida
    # o token do usuário final, mas isso pode ser adicionado para defesa em profundidade.
    # Se o token fosse repassado:
    # downstream_headers = {"Authorization": request.headers.get("Authorization")}
    downstream_headers = {}

    try:
        if method.upper() == "GET":
            response = await collector_service_client.get(
                collector_endpoint, params=params, headers=downstream_headers
            )
        elif method.upper() == "POST": # Assumindo que POSTs enviam JSON
             response = await collector_service_client.post(
                collector_endpoint, data=payload, params=params, headers=downstream_headers, is_json_data=True
            )
        else:
            logger.error(f"Unsupported proxy method: {method} for {collector_endpoint}")
            raise HTTPException(status_code=500, detail=f"Unsupported proxy method: {method}")

        if response.status_code != 200:
            detail_error = response.text
            try:
                detail_json = response.json()
                # Tenta extrair a mensagem de erro mais específica do FastAPI/Pydantic
                if isinstance(detail_json, dict) and "detail" in detail_json:
                    if isinstance(detail_json["detail"], str):
                        detail_error = detail_json["detail"]
                    # Se 'detail' for uma lista de erros de validação Pydantic, formatá-los.
                    elif isinstance(detail_json["detail"], list):
                        error_messages = []
                        for err in detail_json["detail"]:
                            loc = " -> ".join(map(str, err.get("loc", [])))
                            msg = err.get("msg")
                            error_messages.append(f"Field '{loc}': {msg}")
                        detail_error = "; ".join(error_messages)
            except Exception: # Mantém response.text se não for JSON ou não tiver "detail"
                pass

            logger.warning(f"Error from Collector Service ({collector_endpoint}): Status {response.status_code}, Detail: {detail_error}")
            raise HTTPException(
                status_code=response.status_code, # Propaga o status code original
                detail=f"Collector Service error ({collector_endpoint}): {detail_error}",
            )
        return response.json()

    except HTTPException as e: # Re-lança exceções HTTP já tratadas (do http_client ou daqui)
        # Já logado no http_client ou aqui se for erro de status code
        raise e
    except Exception as e: # Captura outras exceções (ex: falha de conexão não tratada pelo http_client)
        logger.exception(f"Unexpected error proxying to collector ({collector_endpoint})")
        raise HTTPException(
            status_code=500, detail=f"Gateway error proxying to collector service ({collector_endpoint}): {str(e)}"
        )

# O prefixo /api/v1 é aplicado em main.py ao incluir este router.
# As rotas aqui começarão com /collect (ou /analyze)
ROUTER_PREFIX = "/collect/aws" # Usado para os endpoints de proxy de coleta

# Atualizando response_model para usar os schemas específicos
@router.get(f"{ROUTER_PREFIX}/s3", response_model=List[collector_s3_schemas.S3BucketData], name="collector:get_s3_data")
async def collect_s3_gateway(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Proxy para coletar dados de S3 buckets."""
    return await _proxy_collector_request("GET", "/collect/s3", current_user, request)

@router.get(f"{ROUTER_PREFIX}/ec2/instances", response_model=List[collector_ec2_schemas.Ec2InstanceData], name="collector:get_ec2_instances")
async def collect_ec2_instances_gateway(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Proxy para coletar dados de instâncias EC2."""
    return await _proxy_collector_request("GET", "/collect/ec2/instances", current_user, request)

@router.get(f"{ROUTER_PREFIX}/ec2/security-groups", response_model=List[collector_ec2_schemas.SecurityGroup], name="collector:get_ec2_security_groups")
async def collect_ec2_security_groups_gateway(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Proxy para coletar dados de Security Groups EC2."""
    return await _proxy_collector_request("GET", "/collect/ec2/security-groups", current_user, request)

@router.get(f"{ROUTER_PREFIX}/iam/users", response_model=List[collector_iam_schemas.IAMUserData], name="collector:get_iam_users")
async def collect_iam_users_gateway(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Proxy para coletar dados de usuários IAM."""
    return await _proxy_collector_request("GET", "/collect/iam/users", current_user, request)

@router.get(f"{ROUTER_PREFIX}/iam/roles", response_model=List[collector_iam_schemas.IAMRoleData], name="collector:get_iam_roles")
async def collect_iam_roles_gateway(
    request: Request, current_user: TokenData = Depends(get_current_user)
):
    """Proxy para coletar dados de roles IAM."""
    return await _proxy_collector_request("GET", "/collect/iam/roles", current_user, request)

@router.get(f"{ROUTER_PREFIX}/iam/policies", response_model=List[collector_iam_schemas.IAMPolicyData], name="collector:get_iam_policies")
async def collect_iam_policies_gateway(
    request: Request,
    scope: str = Query("Local", enum=["All", "AWS", "Local"], description="Escopo das políticas a serem listadas."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de políticas IAM gerenciadas."""
    return await _proxy_collector_request(
        "GET", "/collect/iam/policies", current_user, request, params={"scope": scope}
    )


# --- Endpoints de Análise (Orquestração) ---
# O endpoint /analyze/aws/s3 existente já faz a orquestração.
# Pode ser mantido ou refatorado.
# O prefixo para estes é /analyze/aws (aplicado pelo nome do arquivo/router)
# Atualizando response_model para usar o schema Alert específico
@router.post(
    "/analyze/aws/s3", response_model=List[policy_engine_alert_schema.Alert], name="orchestrator:analyze_s3"
)
async def analyze_s3_data_orchestrated(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Orquestra a coleta de dados S3 e sua análise.
    1. Chama o Collector Service para obter dados S3.
    2. Envia os dados S3 para o Policy Engine Service para análise.
    3. Retorna os alertas gerados.
    """
    downstream_headers = {}
    # auth_header = request.headers.get("Authorization")
    # if auth_header:
    #     downstream_headers["Authorization"] = auth_header

    # 1. Chamar o Collector Service
    s3_collected_data: List[Dict[str, Any]] # Espera-se uma lista de dicts
    try:
        # Chamada direta ao collector service é mais eficiente aqui do que chamar o proxy do próprio gateway.
        collector_response = await collector_service_client.get("/collect/s3", headers=downstream_headers)

        if collector_response.status_code != 200:
            # Tentar obter detalhes do erro do corpo da resposta
            error_detail = collector_response.text
            try:
                error_json = collector_response.json()
                if "detail" in error_json:
                    error_detail = error_json["detail"]
            except: pass
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service (S3) during orchestration: {error_detail}",
            )
        s3_collected_data = collector_response.json()

        if not s3_collected_data: # Lista vazia é um resultado válido
            return []
        # Validação de erro dentro da lista já é feita pelo collector e propagada pelo proxy.
        # Se o collector_service_client.get falhar (ex: timeout), ele levantará HTTPException.

    except HTTPException as e: # Re-lançar exceções já tratadas
        logger.error(f"HTTPException during S3 collection step in orchestration: {e.detail}")
        raise e
    except Exception as e: # Outras exceções
        logger.exception("Error calling Collector Service (S3) during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to collect S3 data for analysis: {str(e)}"
        )

    # 2. Enviar os dados coletados para o Policy Engine Service
    # Ajuste o payload conforme o que o policy-engine-service espera.
    # Exemplo: {"provider": "aws", "service": "s3", "data": s3_collected_data}
    analysis_payload = {"provider": "aws", "service": "s3", "data": s3_collected_data}
    alerts: List[Dict[str, Any]] # Espera-se uma lista de dicts
    try:
        # Endpoint no policy-engine-service (ex: /api/v1/analyze)
        engine_response = await policy_engine_service_client.post(
            "/analyze", data=analysis_payload, headers=downstream_headers # Assumindo que /analyze é o endpoint correto
        )
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try:
                error_json = engine_response.json()
                if "detail" in error_json:
                    error_detail = error_json["detail"]
            except: pass
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service (S3 analysis) during orchestration: {error_detail}",
            )
        alerts = engine_response.json()
    except HTTPException as e: # Re-lançar
        logger.error(f"HTTPException during S3 analysis step in orchestration: {e.detail}")
        raise e
    except Exception as e: # Outras exceções
        logger.exception("Error calling Policy Engine Service (S3) during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to analyze S3 data: {str(e)}"
        )

    return alerts

# --- EC2 Instances Analysis Orchestration ---
@router.post(
    "/analyze/aws/ec2/instances", response_model=List[policy_engine_alert_schema.Alert], name="orchestrator:analyze_ec2_instances"
)
async def analyze_ec2_instances_data_orchestrated(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Orquestra a coleta de dados de Instâncias EC2 e sua análise.
    """
    downstream_headers = {} # Add auth header if needed for downstream
    service_name = "ec2_instances"
    collector_path = "/collect/ec2/instances"

    # 1. Chamar o Collector Service
    collected_data: List[Dict[str, Any]]
    try:
        collector_response = await collector_service_client.get(collector_path, headers=downstream_headers)
        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service ({service_name}) during orchestration: {error_detail}",
            )
        collected_data = collector_response.json()
        if not collected_data: return []
    except HTTPException as e:
        logger.error(f"HTTPException during {service_name} collection step in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Collector Service ({service_name}) during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to collect {service_name} data for analysis: {str(e)}"
        )

    # 2. Enviar os dados coletados para o Policy Engine Service
    analysis_payload = {"provider": "aws", "service": service_name, "data": collected_data}
    alerts: List[Dict[str, Any]]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service ({service_name} analysis) during orchestration: {error_detail}",
            )
        alerts = engine_response.json()
    except HTTPException as e:
        logger.error(f"HTTPException during {service_name} analysis step in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Policy Engine Service ({service_name}) during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to analyze {service_name} data: {str(e)}"
        )
    return alerts

# --- EC2 Security Groups Analysis Orchestration ---
@router.post(
    "/analyze/aws/ec2/security-groups", response_model=List[policy_engine_alert_schema.Alert], name="orchestrator:analyze_ec2_sgs"
)
async def analyze_ec2_sgs_data_orchestrated(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Orquestra a coleta de dados de Security Groups EC2 e sua análise.
    """
    downstream_headers = {}
    service_name = "ec2_security_groups"
    collector_path = "/collect/ec2/security-groups"

    collected_data: List[Dict[str, Any]]
    try:
        collector_response = await collector_service_client.get(collector_path, headers=downstream_headers)
        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=collector_response.status_code, detail=f"Error from Collector Service ({service_name}): {error_detail}")
        collected_data = collector_response.json()
        if not collected_data: return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway failed to collect {service_name} data: {str(e)}")

    analysis_payload = {"provider": "aws", "service": service_name, "data": collected_data}
    alerts: List[Dict[str, Any]]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=engine_response.status_code, detail=f"Error from Policy Engine ({service_name} analysis): {error_detail}")
        alerts = engine_response.json()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway failed to analyze {service_name} data: {str(e)}")
    return alerts

# --- IAM Users Analysis Orchestration ---
@router.post(
    "/analyze/aws/iam/users", response_model=List[policy_engine_alert_schema.Alert], name="orchestrator:analyze_iam_users"
)
async def analyze_iam_users_data_orchestrated(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Orquestra a coleta de dados de Usuários IAM e sua análise.
    """
    downstream_headers = {}
    service_name = "iam_users"
    collector_path = "/collect/iam/users" # Corrigido para o endpoint do collector

    collected_data: List[Dict[str, Any]]
    try:
        collector_response = await collector_service_client.get(collector_path, headers=downstream_headers)
        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=collector_response.status_code, detail=f"Error from Collector Service ({service_name}): {error_detail}")
        collected_data = collector_response.json()
        if not collected_data: return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway failed to collect {service_name} data: {str(e)}")

    analysis_payload = {"provider": "aws", "service": service_name, "data": collected_data}
    alerts: List[Dict[str, Any]]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=engine_response.status_code, detail=f"Error from Policy Engine ({service_name} analysis): {error_detail}")
        alerts = engine_response.json()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gateway failed to analyze {service_name} data: {str(e)}")
    return alerts

# TODO: Adicionar endpoints de orquestração para IAM Roles, IAM Policies.
# TODO: Adicionar um endpoint "/analyze/aws/all" que chama todos os coletores e analisadores.
# Ex: @router.post("/analyze/aws/all", response_model=Any, name="orchestrator:analyze_all_aws")
