from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Any
from app.aws import s3_collector, ec2_collector, iam_collector
from app.schemas.s3 import S3BucketData
from app.schemas.ec2 import Ec2InstanceData, SecurityGroup
from app.schemas.iam import IAMUserData, IAMRoleData, IAMPolicyData

# from app.core.security import get_current_active_user # Se precisarmos de autenticação para este endpoint
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/s3", response_model=List[S3BucketData])
async def collect_s3_data(
    # current_user: Any = Depends(get_current_active_user) # Descomentar se autenticação for necessária
):
    """
    Endpoint para coletar dados de configuração de buckets S3.
    Retorna uma lista de dados de buckets S3 ou levanta HTTPException em caso de erro global.
    Erros específicos de bucket são incluídos no campo 'error_details' de cada item da lista.
    """
    try:
        data = await s3_collector.get_s3_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during S3 data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_s3_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/ec2/instances", response_model=List[Ec2InstanceData])
async def collect_ec2_instances_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de instâncias EC2 de todas as regiões habilitadas.
    Erros de coleta em uma região específica podem ser indicados no campo 'error_details'
    do objeto Ec2InstanceData correspondente a essa região (com instance_id="ERROR_REGION").
    """
    try:
        data = await ec2_collector.get_ec2_instance_data_all_regions()
        return data
    except HTTPException as http_exc: # Erros globais como falha de credenciais em get_all_regions
        logger.error(f"HTTPException during EC2 instance data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_ec2_instances_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/ec2/security-groups", response_model=List[SecurityGroup])
async def collect_ec2_security_groups_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de Security Groups EC2 de todas as regiões habilitadas.
    Falhas na coleta de uma região específica são logadas, mas a coleta continua para outras regiões.
    O endpoint pode retornar uma lista parcial se algumas regiões falharem.
    """
    try:
        data = await ec2_collector.get_security_group_data_all_regions()
        return data
    except HTTPException as http_exc: # Erros globais como falha de credenciais em get_all_regions
        logger.error(f"HTTPException during EC2 Security Group data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_ec2_security_groups_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )


@router.get("/iam/users", response_model=List[IAMUserData])
async def collect_iam_users_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de usuários IAM.
    """
    try:
        data = await iam_collector.get_iam_users_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during IAM users data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_iam_users_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/iam/roles", response_model=List[IAMRoleData])
async def collect_iam_roles_data(
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de roles IAM.
    """
    try:
        data = await iam_collector.get_iam_roles_data()
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during IAM roles data collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_iam_roles_data endpoint")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

@router.get("/iam/policies", response_model=List[IAMPolicyData])
async def collect_iam_policies_data(
    scope: str = Query("Local", enum=["All", "AWS", "Local"]),
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Endpoint para coletar dados de políticas IAM gerenciadas.
    Use o parâmetro 'scope' para filtrar por 'All', 'AWS', ou 'Local' (padrão).
    """
    try:
        data = await iam_collector.get_iam_policies_data(scope=scope)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during AWS IAM policies data collection (scope: {scope}): {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_iam_policies_data (AWS) endpoint (scope: {scope})")
        raise HTTPException(
            status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}"
        )

# --- Endpoints de Coleta GCP ---
from app.gcp import gcp_storage_collector, gcp_compute_collector, gcp_iam_collector
from app.schemas import gcp_storage, gcp_compute, gcp_iam # Importar os schemas GCP

GCP_ROUTER_PREFIX = "/collect/gcp"

@router.get(f"{GCP_ROUTER_PREFIX}/storage/buckets", response_model=List[gcp_storage.GCPStorageBucketData], name="gcp_collector:get_storage_buckets")
async def collect_gcp_storage_buckets_data(
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP. Se não fornecido, tenta obter do ambiente."),
    # current_user: Any = Depends(get_current_active_user) # Adicionar autenticação se necessário
):
    """Coleta dados de configuração de Google Cloud Storage buckets."""
    try:
        # A função de coleta no collector já lida com project_id None e tenta obter do ambiente.
        data = await gcp_storage_collector.get_gcp_storage_buckets(project_id=project_id)
        # Se a coleta falhar e retornar um item de erro, a validação do response_model pode pegar se não for o schema esperado.
        # Idealmente, o collector levantaria HTTPException para erros globais.
        if data and data[0].error_details and data[0].id.startswith("ERROR_"): # Checagem básica de erro retornado como dado
            # Se for um erro global retornado como o único item da lista.
            if "Project ID is required" in data[0].error_details:
                 raise HTTPException(status_code=400, detail=data[0].error_details) # Bad Request se project_id é mandatório e não encontrado
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP Storage Buckets collection for project {project_id or 'default'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_storage_buckets_data endpoint for project {project_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/compute/instances", response_model=List[gcp_compute.GCPComputeInstanceData], name="gcp_collector:get_compute_instances")
async def collect_gcp_compute_instances_data(
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP. Se não fornecido, tenta obter do ambiente."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de instâncias de VM do Google Compute Engine."""
    try:
        data = await gcp_compute_collector.get_gcp_compute_instances(project_id=project_id)
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            if "Project ID is required" in data[0].error_details:
                 raise HTTPException(status_code=400, detail=data[0].error_details)
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP Compute Instances collection for project {project_id or 'default'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_compute_instances_data endpoint for project {project_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/compute/firewalls", response_model=List[gcp_compute.GCPFirewallData], name="gcp_collector:get_compute_firewalls")
async def collect_gcp_compute_firewalls_data(
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP. Se não fornecido, tenta obter do ambiente."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de regras de Firewall VPC do Google Cloud."""
    try:
        data = await gcp_compute_collector.get_gcp_firewall_rules(project_id=project_id)
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            if "Project ID is required" in data[0].error_details:
                 raise HTTPException(status_code=400, detail=data[0].error_details)
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP Firewall Rules collection for project {project_id or 'default'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_compute_firewalls_data endpoint for project {project_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/iam/project-policies", response_model=Optional[gcp_iam.GCPProjectIAMPolicyData], name="gcp_collector:get_project_iam_policy")
async def collect_gcp_project_iam_policy_data(
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP. Se não fornecido, tenta obter do ambiente."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta a política IAM a nível de projeto do Google Cloud."""
    try:
        data = await gcp_iam_collector.get_gcp_project_iam_policy(project_id=project_id)
        if data is None: # Collector pode retornar None se o project_id for estritamente necessário e não encontrado
             raise HTTPException(status_code=400, detail="GCP Project ID is required and could not be determined for IAM policy collection.")
        if data.error_details and data.project_id == project_id : # Erro específico na coleta desta política
            raise HTTPException(status_code=500, detail=data.error_details)
        return data
    except HTTPException as http_exc: # Exceções levantadas pelo gcp_iam_collector (ex: get_iam_client falha)
        logger.error(f"HTTPException during GCP Project IAM Policy collection for project {project_id or 'default'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_project_iam_policy_data endpoint for project {project_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
