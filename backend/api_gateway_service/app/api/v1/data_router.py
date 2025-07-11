from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Dict, Any, Optional
from app.services.http_client import (
    collector_service_client,
    policy_engine_service_client,
)
from app.core.security import get_current_user, TokenData

# Importar os schemas copiados/criados para o gateway
from app.schemas import (
# Importar os schemas copiados/criados para o gateway
from app.schemas import (
    collector_s3_schemas, collector_ec2_schemas, collector_iam_schemas, collector_rds_schemas,
    collector_gcp_storage_schemas, collector_gcp_compute_schemas, collector_gcp_iam_schemas, collector_gke_schemas, # Adicionado GKE
    collector_huawei_obs_schemas, collector_huawei_ecs_schemas, collector_huawei_iam_schemas,
    collector_azure_schemas,
    collector_google_workspace_schemas,
    policy_engine_alert_schema
)
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

# --- Endpoints de Coleta GCP (Proxy para Collector Service) ---
GCP_COLLECT_ROUTER_PREFIX = "/collect/gcp"

@router.get(f"{GCP_COLLECT_ROUTER_PREFIX}/storage/buckets", response_model=List[collector_gcp_storage_schemas.GCPStorageBucketData], name="gcp_collector:get_storage_buckets")
async def collect_gcp_storage_buckets_gateway(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Google Cloud Storage buckets."""
    # O collector_endpoint deve ser o path no collector service, não incluindo o prefixo do gateway.
    # O _proxy_collector_request já adiciona o base_url do collector_service_client.
    return await _proxy_collector_request("GET", "/collect/gcp/storage/buckets", current_user, request, params={"project_id": project_id} if project_id else None)

@router.get(f"{GCP_COLLECT_ROUTER_PREFIX}/compute/instances", response_model=List[collector_gcp_compute_schemas.GCPComputeInstanceData], name="gcp_collector:get_compute_instances")
async def collect_gcp_compute_instances_gateway(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de instâncias de VM do Google Compute Engine."""
    return await _proxy_collector_request("GET", "/collect/gcp/compute/instances", current_user, request, params={"project_id": project_id} if project_id else None)

@router.get(f"{GCP_COLLECT_ROUTER_PREFIX}/compute/firewalls", response_model=List[collector_gcp_compute_schemas.GCPFirewallData], name="gcp_collector:get_compute_firewalls")
async def collect_gcp_compute_firewalls_gateway(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de regras de Firewall VPC do Google Cloud."""
    return await _proxy_collector_request("GET", "/collect/gcp/compute/firewalls", current_user, request, params={"project_id": project_id} if project_id else None)

@router.get(f"{GCP_COLLECT_ROUTER_PREFIX}/iam/project-policies", response_model=Optional[collector_gcp_iam_schemas.GCPProjectIAMPolicyData], name="gcp_collector:get_project_iam_policy")
async def collect_gcp_project_iam_policy_gateway(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar a política IAM a nível de projeto do Google Cloud."""
    return await _proxy_collector_request("GET", "/collect/gcp/iam/project-policies", current_user, request, params={"project_id": project_id} if project_id else None)

# --- GCP GKE Collector Proxy ---
@router.get(f"{GCP_COLLECT_ROUTER_PREFIX}/gke/clusters", response_model=List[collector_gke_schemas.GKEClusterData], name="gcp_collector:get_gke_clusters")
async def collect_gke_clusters_gateway(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP."),
    location: str = Query("-", description="Location (região/zona ou '-') para listar clusters GKE."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de clusters GKE."""
    params = {"location": location}
    if project_id:
        params["project_id"] = project_id
    return await _proxy_collector_request("GET", "/collect/gcp/gke/clusters", current_user, request, params=params)


# --- Endpoints de Análise GCP (Orquestração) ---
GCP_ANALYZE_ROUTER_PREFIX = "/analyze/gcp" # Mantém o mesmo prefixo para organização

async def _orchestrate_gcp_analysis(
    service_name_in_engine: str,
    collector_path_suffix: str,
    request: Request,
    project_id: Optional[str],
    current_user: TokenData,
    additional_collector_params: Optional[Dict[str, Any]] = None # Para parâmetros extras como 'location' para GKE
) -> List[policy_engine_alert_schema.AlertSchema]: # Retorna AlertSchema do gateway
    downstream_headers = {}

    # 1. Chamar o Collector Service
    collected_data: Any
    try:
        # O collector_controller no collector_service espera paths como /gcp/storage/buckets
        # O prefixo /api/v1/collect é adicionado no main.py do collector_service
        # Então, a chamada ao client deve ser para o path relativo ao prefixo do controller
        # Ex: "/gcp/" + collector_path_suffix
        final_collector_path = f"/gcp/{collector_path_suffix}"

        collector_params = {"project_id": project_id} if project_id else {}
        if additional_collector_params:
            collector_params.update(additional_collector_params)

        collector_response = await collector_service_client.get(final_collector_path, params=collector_params, headers=downstream_headers)

        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service (GCP {collector_path_suffix}) for project {project_id or 'default'}: {error_detail}",
            )
        collected_data = collector_response.json()
        if not collected_data and service_name_in_engine != "gcp_iam_project_policies": # IAM pode retornar None
             return []
    except HTTPException as e:
        logger.error(f"HTTPException during GCP {collector_path_suffix} collection for project {project_id or 'default'} in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Collector Service (GCP {collector_path_suffix}) for project {project_id or 'default'} during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to collect GCP {collector_path_suffix} data for analysis: {str(e)}"
        )

    # 2. Enviar os dados coletados para o Policy Engine Service
    analysis_payload = {
        "provider": "gcp",
        "service": service_name_in_engine,
        "data": collected_data,
        "account_id": project_id
    }
    alerts: List[policy_engine_alert_schema.AlertSchema]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service (GCP {service_name_in_engine} analysis for project {project_id or 'default'}): {error_detail}",
            )
        alerts = engine_response.json()
    except HTTPException as e:
        logger.error(f"HTTPException during GCP {service_name_in_engine} analysis for project {project_id or 'default'} in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Policy Engine Service (GCP {service_name_in_engine}) for project {project_id or 'default'} during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to analyze GCP {service_name_in_engine} data: {str(e)}"
        )
    return alerts

@router.post(f"{GCP_ANALYZE_ROUTER_PREFIX}/storage/buckets", response_model=List[policy_engine_alert_schema.AlertSchema], name="gcp_orchestrator:analyze_storage_buckets")
async def analyze_gcp_storage_buckets_orchestrated(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP a ser analisado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Google Cloud Storage buckets."""
    if not project_id:
        raise HTTPException(status_code=400, detail="GCP Project ID is required for analysis.")
    return await _orchestrate_gcp_analysis(
        service_name_in_engine="gcp_storage_buckets",
        collector_path_suffix="storage/buckets",
        request=request, project_id=project_id, current_user=current_user
    )

@router.post(f"{GCP_ANALYZE_ROUTER_PREFIX}/compute/instances", response_model=List[policy_engine_alert_schema.Alert], name="gcp_orchestrator:analyze_compute_instances")
async def analyze_gcp_compute_instances_orchestrated(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP a ser analisado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de instâncias de VM do Google Compute Engine."""
    if not project_id:
        raise HTTPException(status_code=400, detail="GCP Project ID is required for analysis.")
    return await _orchestrate_gcp_analysis(
        service_name_in_engine="gcp_compute_instances",
        collector_path_suffix="compute/instances",
        request=request, project_id=project_id, current_user=current_user
    )

@router.post(f"{GCP_ANALYZE_ROUTER_PREFIX}/compute/firewalls", response_model=List[policy_engine_alert_schema.Alert], name="gcp_orchestrator:analyze_compute_firewalls")
async def analyze_gcp_compute_firewalls_orchestrated(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP a ser analisado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de regras de Firewall VPC do Google Cloud."""
    if not project_id:
        raise HTTPException(status_code=400, detail="GCP Project ID is required for analysis.")
    return await _orchestrate_gcp_analysis(
        service_name_in_engine="gcp_compute_firewalls",
        collector_path_suffix="compute/firewalls",
        request=request, project_id=project_id, current_user=current_user
    )

@router.post(f"{GCP_ANALYZE_ROUTER_PREFIX}/iam/project-policies", response_model=List[policy_engine_alert_schema.Alert], name="gcp_orchestrator:analyze_project_iam_policy")
async def analyze_gcp_project_iam_policy_orchestrated(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP a ser analisado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise da política IAM a nível de projeto do Google Cloud."""
    if not project_id:
        raise HTTPException(status_code=400, detail="GCP Project ID is required for analysis.")
    return await _orchestrate_gcp_analysis(
        service_name_in_engine="gcp_iam_project_policies",
        collector_path_suffix="iam/project-policies",
        request=request, project_id=project_id, current_user=current_user
    )

@router.post(f"{GCP_ANALYZE_ROUTER_PREFIX}/gke/clusters", response_model=List[policy_engine_alert_schema.AlertSchema], name="gcp_orchestrator:analyze_gke_clusters")
async def analyze_gke_clusters_orchestrated(
    request: Request,
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP a ser analisado."),
    location: str = Query("-", description="Location (região/zona ou '-') para GKE clusters."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Google Kubernetes Engine (GKE) clusters."""
    if not project_id:
        raise HTTPException(status_code=400, detail="GCP Project ID is required for GKE analysis.")
    return await _orchestrate_gcp_analysis(
        service_name_in_engine="gke_clusters", # Como o policy engine espera
        collector_path_suffix="gke/clusters",  # Path no collector após /gcp/
        request=request, project_id=project_id, current_user=current_user,
        additional_collector_params={"location": location} # Passar location para o coletor GKE
    )


# TODO: Adicionar endpoints de orquestração para AWS IAM Roles, IAM Policies.

# --- Endpoints de Coleta Huawei Cloud (Proxy) ---
HUAWEI_COLLECT_ROUTER_PREFIX = "/collect/huawei" # Este prefixo não é mais usado aqui

@router.get(f"{HUAWEI_COLLECT_ROUTER_PREFIX}/obs/buckets", response_model=List[collector_huawei_obs_schemas.HuaweiOBSBucketData], name="huawei_collector:get_obs_buckets")
async def collect_huawei_obs_buckets_gateway(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Huawei Cloud OBS buckets."""
    params = {"project_id": project_id, "region_id": region_id}
    return await _proxy_collector_request("GET", "/collect/huawei/obs/buckets", current_user, request, params=params)

@router.get(f"{HUAWEI_COLLECT_ROUTER_PREFIX}/ecs/instances", response_model=List[collector_huawei_ecs_schemas.HuaweiECSServerData], name="huawei_collector:get_ecs_instances")
async def collect_huawei_ecs_instances_gateway(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de instâncias ECS (VMs) da Huawei Cloud."""
    params = {"project_id": project_id, "region_id": region_id}
    return await _proxy_collector_request("GET", "/collect/huawei/ecs/instances", current_user, request, params=params)

@router.get(f"{HUAWEI_COLLECT_ROUTER_PREFIX}/vpc/security-groups", response_model=List[collector_huawei_ecs_schemas.HuaweiVPCSecurityGroup], name="huawei_collector:get_vpc_sgs")
async def collect_huawei_vpc_sgs_gateway(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Security Groups VPC da Huawei Cloud."""
    params = {"project_id": project_id, "region_id": region_id}
    return await _proxy_collector_request("GET", "/collect/huawei/vpc/security-groups", current_user, request, params=params)

@router.get(f"{HUAWEI_COLLECT_ROUTER_PREFIX}/iam/users", response_model=List[collector_huawei_iam_schemas.HuaweiIAMUserData], name="huawei_collector:get_iam_users")
async def collect_huawei_iam_users_gateway(
    request: Request,
    region_id: str = Query(..., description="ID da Região Huawei Cloud para instanciar o cliente IAM."),
    domain_id: Optional[str] = Query(None, description="ID do Domínio (Conta) Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de usuários IAM da Huawei Cloud."""
    params = {"region_id": region_id}
    if domain_id:
        params["domain_id"] = domain_id
    return await _proxy_collector_request("GET", "/collect/huawei/iam/users", current_user, request, params=params)


# --- Endpoints de Análise Huawei Cloud (Orquestração) ---
HUAWEI_ANALYZE_ROUTER_PREFIX = "/analyze/huawei"

async def _orchestrate_huawei_analysis(
    service_name_in_engine: str, # ex: "huawei_obs_buckets"
    collector_path_suffix: str,  # ex: "obs/buckets"
    request: Request,
    project_id: str, # Para Huawei, pode ser Project ID ou Domain ID dependendo do serviço
    region_id: str, # Necessário para a maioria dos coletores Huawei
    current_user: TokenData,
    domain_id_for_iam: Optional[str] = None # Específico para IAM Users
) -> List[policy_engine_alert_schema.Alert]:
    downstream_headers = {}

    collected_data: Any
    try:
        collector_full_path = f"/collect/huawei/{collector_path_suffix}"
        collector_params = {"project_id": project_id, "region_id": region_id}
        if service_name_in_engine == "huawei_iam_users": # IAM usa domain_id
            collector_params = {"region_id": region_id}
            if domain_id_for_iam: # Se domain_id específico for fornecido para IAM
                collector_params["domain_id"] = domain_id_for_iam
            # Se domain_id_for_iam não for fornecido, o coletor IAM tentará usar HUAWEICLOUD_SDK_DOMAIN_ID
            # ou o project_id das credenciais como fallback. O account_id para o policy engine será o project_id.

        collector_response = await collector_service_client.get(collector_full_path, params=collector_params, headers=downstream_headers)

        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service (Huawei {collector_path_suffix}) for account {project_id}/{domain_id_for_iam or 'N/A'} in region {region_id}: {error_detail}",
            )
        collected_data = collector_response.json()
        if not collected_data: return []
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to collect Huawei {collector_path_suffix} data: {str(e)}"
        )

    analysis_payload = {
        "provider": "huawei",
        "service": service_name_in_engine,
        "data": collected_data,
        "account_id": domain_id_for_iam if service_name_in_engine == "huawei_iam_users" else project_id,
        # Adicionar region_id ao payload se as políticas precisarem dele e não estiver no 'data' individual.
        # Para Huawei, ECS e SGs têm region_id no schema. OBS tem location. IAM é global.
    }
    alerts: List[policy_engine_alert_schema.Alert]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service (Huawei {service_name_in_engine} analysis): {error_detail}",
            )
        alerts = engine_response.json()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to analyze Huawei {service_name_in_engine} data: {str(e)}"
        )
    return alerts

@router.post(f"{HUAWEI_ANALYZE_ROUTER_PREFIX}/obs/buckets", response_model=List[policy_engine_alert_schema.Alert], name="huawei_orchestrator:analyze_obs_buckets")
async def analyze_huawei_obs_buckets_orchestrated(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud onde os buckets serão listados/verificados."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Huawei Cloud OBS buckets."""
    return await _orchestrate_huawei_analysis(
        service_name_in_engine="huawei_obs_buckets",
        collector_path_suffix="obs/buckets",
        request=request, project_id=project_id, region_id=region_id, current_user=current_user
    )

@router.post(f"{HUAWEI_ANALYZE_ROUTER_PREFIX}/ecs/instances", response_model=List[policy_engine_alert_schema.Alert], name="huawei_orchestrator:analyze_ecs_instances")
async def analyze_huawei_ecs_instances_orchestrated(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de instâncias ECS (VMs) da Huawei Cloud."""
    return await _orchestrate_huawei_analysis(
        service_name_in_engine="huawei_ecs_instances",
        collector_path_suffix="ecs/instances",
        request=request, project_id=project_id, region_id=region_id, current_user=current_user
    )

@router.post(f"{HUAWEI_ANALYZE_ROUTER_PREFIX}/vpc/security-groups", response_model=List[policy_engine_alert_schema.Alert], name="huawei_orchestrator:analyze_vpc_sgs")
async def analyze_huawei_vpc_sgs_orchestrated(
    request: Request,
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Security Groups VPC da Huawei Cloud."""
    return await _orchestrate_huawei_analysis(
        service_name_in_engine="huawei_vpc_security_groups",
        collector_path_suffix="vpc/security-groups",
        request=request, project_id=project_id, region_id=region_id, current_user=current_user
    )

@router.post(f"{HUAWEI_ANALYZE_ROUTER_PREFIX}/iam/users", response_model=List[policy_engine_alert_schema.Alert], name="huawei_orchestrator:analyze_iam_users")
async def analyze_huawei_iam_users_orchestrated(
    request: Request,
    region_id: str = Query(..., description="ID da Região Huawei Cloud para instanciar o cliente IAM (endpoint)."),
    domain_id: Optional[str] = Query(None, description="ID do Domínio (Conta) Huawei Cloud. Se não fornecido, o coletor tentará usar variáveis de ambiente ou o project_id das credenciais."),
    # O project_id da conta/credenciais principal é usado como 'account_id' para o policy engine se domain_id não for o foco.
    # Para IAM, o 'account_id' no payload do policy engine será o domain_id.
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de usuários IAM da Huawei Cloud."""
    # O `_orchestrate_huawei_analysis` espera `project_id` para o account_id geral.
    # Para IAM, passamos o `domain_id` (ou um placeholder se não fornecido) como `domain_id_for_iam`.
    # O `account_id` no payload para o policy engine será o `domain_id` para `huawei_iam_users`.
    # Se `domain_id` for None, o coletor tentará resolver.
    # O `project_id` aqui é o da conta principal, que pode ser o mesmo que o `domain_id` ou um `project_id` dentro desse domínio.
    # Para consistência, o `account_id` que o motor de políticas recebe para IAM deve ser o `domain_id`.
    # O `project_id` passado para `_orchestrate_huawei_analysis` será usado como `account_id` no payload para o motor,
    # exceto para o caso de IAM Users onde o `domain_id_for_iam` tomará precedência.

    # Usar um project_id dummy para a chamada _orchestrate_huawei_analysis, pois ele será
    # sobrescrito pelo domain_id_for_iam para o `account_id` do payload do Policy Engine.
    # O importante é que o collector_params para IAM use o domain_id.
    dummy_project_id_for_orchestrator = domain_id or "huawei-iam-domain-scope"

    return await _orchestrate_huawei_analysis(
        service_name_in_engine="huawei_iam_users",
        collector_path_suffix="iam/users",
        request=request,
        project_id=dummy_project_id_for_orchestrator, # Usado como account_id geral, mas para IAM, domain_id_for_iam é mais específico.
        region_id=region_id,
        current_user=current_user,
        domain_id_for_iam=domain_id
    )

# TODO: Adicionar um endpoint "/analyze/aws/all", "/analyze/gcp/all" e "/analyze/huawei/all"
# que chamam todos os coletores e analisadores para o respectivo provedor.
# Ex: @router.post("/analyze/huawei/all", response_model=List[policy_engine_alert_schema.Alert], name="huawei_orchestrator:analyze_all_huawei")


# --- Endpoints de Coleta Azure (Proxy) ---
AZURE_COLLECT_ROUTER_PREFIX = "/collect/azure"

@router.get(f"{AZURE_COLLECT_ROUTER_PREFIX}/virtualmachines", response_model=List[collector_azure_schemas.AzureVirtualMachineData], name="azure_collector:get_virtual_machines")
async def collect_azure_vms_gateway(
    request: Request,
    subscription_id: Optional[str] = Query(None, description="ID da Subscrição Azure."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Azure Virtual Machines."""
    return await _proxy_collector_request("GET", "/collect/azure/virtualmachines", current_user, request, params={"subscription_id": subscription_id} if subscription_id else None)

@router.get(f"{AZURE_COLLECT_ROUTER_PREFIX}/storageaccounts", response_model=List[collector_azure_schemas.AzureStorageAccountData], name="azure_collector:get_storage_accounts")
async def collect_azure_storage_accounts_gateway(
    request: Request,
    subscription_id: Optional[str] = Query(None, description="ID da Subscrição Azure."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Azure Storage Accounts."""
    return await _proxy_collector_request("GET", "/collect/azure/storageaccounts", current_user, request, params={"subscription_id": subscription_id} if subscription_id else None)


# --- Endpoints de Análise Azure (Orquestração) ---
AZURE_ANALYZE_ROUTER_PREFIX = "/analyze/azure"

async def _orchestrate_azure_analysis(
    service_name_in_engine: str, # ex: "azure_virtual_machines"
    collector_path_suffix: str,  # ex: "virtualmachines"
    request: Request,
    subscription_id: Optional[str],
    current_user: TokenData
) -> List[policy_engine_alert_schema.Alert]:
    downstream_headers = {}
    if not subscription_id:
        raise HTTPException(status_code=400, detail="Azure Subscription ID is required for analysis.")

    # 1. Chamar o Collector Service
    collected_data: Any
    try:
        collector_full_path = f"/collect/azure/{collector_path_suffix}"
        collector_params = {"subscription_id": subscription_id}

        collector_response = await collector_service_client.get(collector_full_path, params=collector_params, headers=downstream_headers)

        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=collector_response.status_code,
                detail=f"Error from Collector Service (Azure {collector_path_suffix}) for subscription {subscription_id}: {error_detail}",
            )
        collected_data = collector_response.json()
        if not collected_data: return []
    except HTTPException as e:
        logger.error(f"HTTPException during Azure {collector_path_suffix} collection for subscription {subscription_id} in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Collector Service (Azure {collector_path_suffix}) for subscription {subscription_id} during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to collect Azure {collector_path_suffix} data for analysis: {str(e)}"
        )

    # 2. Enviar os dados coletados para o Policy Engine Service
    analysis_payload = {
        "provider": "azure",
        "service": service_name_in_engine,
        "data": collected_data,
        "account_id": subscription_id # Usar subscription_id como account_id para Azure
    }
    alerts: List[policy_engine_alert_schema.Alert]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(
                status_code=engine_response.status_code,
                detail=f"Error from Policy Engine Service (Azure {service_name_in_engine} analysis for subscription {subscription_id}): {error_detail}",
            )
        alerts = engine_response.json()
    except HTTPException as e:
        logger.error(f"HTTPException during Azure {service_name_in_engine} analysis for subscription {subscription_id} in orchestration: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Policy Engine Service (Azure {service_name_in_engine}) for subscription {subscription_id} during orchestration")
        raise HTTPException(
            status_code=500, detail=f"Gateway failed to analyze Azure {service_name_in_engine} data: {str(e)}"
        )
    return alerts

@router.post(f"{AZURE_ANALYZE_ROUTER_PREFIX}/virtualmachines", response_model=List[policy_engine_alert_schema.Alert], name="azure_orchestrator:analyze_virtual_machines")
async def analyze_azure_vms_orchestrated(
    request: Request,
    subscription_id: str = Query(..., description="ID da Subscrição Azure a ser analisada."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Azure Virtual Machines."""
    return await _orchestrate_azure_analysis(
        service_name_in_engine="azure_virtual_machines", # Nome do serviço como esperado pelo Policy Engine
        collector_path_suffix="virtualmachines",
        request=request, subscription_id=subscription_id, current_user=current_user
    )

@router.post(f"{AZURE_ANALYZE_ROUTER_PREFIX}/storageaccounts", response_model=List[policy_engine_alert_schema.Alert], name="azure_orchestrator:analyze_storage_accounts")
async def analyze_azure_storage_accounts_orchestrated(
    request: Request,
    subscription_id: str = Query(..., description="ID da Subscrição Azure a ser analisada."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Azure Storage Accounts."""
    return await _orchestrate_azure_analysis(
        service_name_in_engine="azure_storage_accounts", # Nome do serviço como esperado pelo Policy Engine
        collector_path_suffix="storageaccounts",
        request=request, subscription_id=subscription_id, current_user=current_user
    )

# --- Endpoints de Coleta Google Workspace (Proxy) ---
GOOGLE_WORKSPACE_COLLECT_ROUTER_PREFIX = "/collect/googleworkspace"

@router.get(f"{GOOGLE_WORKSPACE_COLLECT_ROUTER_PREFIX}/users", response_model=collector_google_workspace_schemas.GoogleWorkspaceUserCollection, name="google_workspace_collector:get_users")
async def collect_google_workspace_users_gateway(
    request: Request,
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace (e.g., 'my_customer' ou C0xxxxxxx)."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado para impersonação."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de usuários do Google Workspace."""
    params = {}
    if customer_id:
        params["customer_id"] = customer_id
    if delegated_admin_email:
        params["delegated_admin_email"] = delegated_admin_email
    return await _proxy_collector_request("GET", "/collect/googleworkspace/users", current_user, request, params=params if params else None)

@router.get(f"{GOOGLE_WORKSPACE_COLLECT_ROUTER_PREFIX}/drive/shared-drives", response_model=List[collector_google_workspace_schemas.SharedDriveData], name="google_workspace_collector:get_shared_drives")
async def collect_gws_shared_drives_gateway(
    request: Request,
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de Drives Compartilhados do Google Workspace."""
    params = {}
    if customer_id:
        params["customer_id"] = customer_id
    if delegated_admin_email:
        params["delegated_admin_email"] = delegated_admin_email
    return await _proxy_collector_request("GET", "/collect/googleworkspace/drive/shared-drives", current_user, request, params=params if params else None)

@router.get(f"{GOOGLE_WORKSPACE_COLLECT_ROUTER_PREFIX}/drive/public-files", response_model=List[collector_google_workspace_schemas.DriveFileData], name="google_workspace_collector:get_public_files")
async def collect_gws_public_files_gateway(
    request: Request,
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy para coletar dados de arquivos públicos/link-shared do Google Drive (MVP pode ser limitado)."""
    params = {}
    if customer_id:
        params["customer_id"] = customer_id
    if delegated_admin_email:
        params["delegated_admin_email"] = delegated_admin_email
    return await _proxy_collector_request("GET", "/collect/googleworkspace/drive/public-files", current_user, request, params=params if params else None)


# --- Endpoints de Análise Google Workspace (Orquestração) ---
GOOGLE_WORKSPACE_ANALYZE_ROUTER_PREFIX = "/analyze/googleworkspace"

async def _orchestrate_google_workspace_analysis(
    service_name_in_engine: str, # ex: "google_workspace_users", "google_drive_shared_drives"
    collector_path_suffix: str,  # ex: "users", "drive/shared-drives"
    request: Request,
    customer_id: Optional[str],
    delegated_admin_email: Optional[str],
    current_user: TokenData,
    data_key_in_collection: str = "users" # Chave onde a lista de dados está no objeto de coleção (ex: "users" para UserCollection)
) -> List[policy_engine_alert_schema.Alert]:
    downstream_headers = {}
    account_id_for_engine = customer_id or settings.GOOGLE_WORKSPACE_CUSTOMER_ID # Usar settings para default

    # 1. Chamar o Collector Service
    collected_data_items: List[Any] # Lista de itens de dados (ex: lista de usuários, lista de drives)
    try:
        collector_full_path = f"/collect/googleworkspace/{collector_path_suffix}"
        collector_params = {}
        if customer_id: collector_params["customer_id"] = customer_id
        if delegated_admin_email: collector_params["delegated_admin_email"] = delegated_admin_email

        collector_response = await collector_service_client.get(collector_full_path, params=collector_params if collector_params else None, headers=downstream_headers)

        if collector_response.status_code != 200:
            error_detail = collector_response.text
            try: error_detail = collector_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=collector_response.status_code, detail=f"Error from Collector Service (GWS {collector_path_suffix}) for customer {account_id_for_engine}: {error_detail}")

        response_json = collector_response.json()

        # Tratar se a resposta é diretamente uma lista (ex: SharedDriveData) ou um objeto de coleção (ex: UserCollection)
        if isinstance(response_json, list):
            collected_data_items = response_json
        elif isinstance(response_json, dict):
            if response_json.get("error_message"):
                raise HTTPException(status_code=500, detail=f"Collector Service error (GWS {collector_path_suffix}): {response_json['error_message']}")
            collected_data_items = response_json.get(data_key_in_collection, [])
        else:
            logger.error(f"Resposta inesperada do coletor GWS {collector_path_suffix}: {response_json}")
            raise HTTPException(status_code=500, detail=f"Resposta inesperada do coletor GWS {collector_path_suffix}")

        if not collected_data_items: return []

    except HTTPException as e:
        logger.error(f"HTTPException during GWS {collector_path_suffix} collection for customer {account_id_for_engine}: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Collector Service (GWS {collector_path_suffix}) for customer {account_id_for_engine}")
        raise HTTPException(status_code=500, detail=f"Gateway failed to collect GWS {collector_path_suffix} data: {str(e)}")

    # 2. Enviar os dados coletados para o Policy Engine Service
    analysis_payload = {
        "provider": "google_workspace",
        "service": service_name_in_engine,
        "data": collected_data_items,
        "account_id": account_id_for_engine
    }
    alerts: List[policy_engine_alert_schema.Alert]
    try:
        engine_response = await policy_engine_service_client.post("/analyze", data=analysis_payload, headers=downstream_headers)
        if engine_response.status_code != 200:
            error_detail = engine_response.text
            try: error_detail = engine_response.json().get("detail", error_detail)
            except: pass
            raise HTTPException(status_code=engine_response.status_code, detail=f"Error from Policy Engine (GWS {service_name_in_engine} analysis for {account_id_for_engine}): {error_detail}")
        alerts = engine_response.json()
    except HTTPException as e:
        logger.error(f"HTTPException during GWS {service_name_in_engine} analysis for {account_id_for_engine}: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Error calling Policy Engine (GWS {service_name_in_engine}) for {account_id_for_engine}")
        raise HTTPException(status_code=500, detail=f"Gateway failed to analyze GWS {service_name_in_engine} data: {str(e)}")
    return alerts

@router.post(f"{GOOGLE_WORKSPACE_ANALYZE_ROUTER_PREFIX}/users", response_model=List[policy_engine_alert_schema.Alert], name="google_workspace_orchestrator:analyze_users")
async def analyze_google_workspace_users_orchestrated(
    request: Request,
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace. Default das settings se não fornecido."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado. Default das settings se não fornecido."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de usuários do Google Workspace."""
    return await _orchestrate_google_workspace_analysis(
        service_name_in_engine="google_workspace_users",
        collector_path_suffix="users",
        request=request,
        customer_id=customer_id,
        delegated_admin_email=delegated_admin_email,
        current_user=current_user,
        data_key_in_collection="users" # Chave no GoogleWorkspaceUserCollection
    )

@router.post(f"{GOOGLE_WORKSPACE_ANALYZE_ROUTER_PREFIX}/drive/shared-drives", response_model=List[policy_engine_alert_schema.Alert], name="google_workspace_orchestrator:analyze_shared_drives")
async def analyze_gws_shared_drives_orchestrated(
    request: Request,
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado."),
    current_user: TokenData = Depends(get_current_user),
):
    """Orquestra a coleta e análise de Drives Compartilhados do Google Workspace."""
    return await _orchestrate_google_workspace_analysis(
        service_name_in_engine="google_drive_shared_drives", # Nome do serviço no Policy Engine
        collector_path_suffix="drive/shared-drives",    # Path no Collector Service
        request=request,
        customer_id=customer_id,
        delegated_admin_email=delegated_admin_email,
        current_user=current_user,
        data_key_in_collection=None # Assumindo que o coletor de shared drives retorna List[SharedDriveData] diretamente
    )

# TODO: Adicionar endpoint para /analyze/googleworkspace/drive/public-files se a coleta for robustecida.
# Por enquanto, a análise de arquivos públicos está integrada na análise de shared-drives.

# TODO: Adicionar endpoints para Gmail, etc. quando os coletores e políticas estiverem prontos.
