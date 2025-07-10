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
        if data is None:
             raise HTTPException(status_code=400, detail="GCP Project ID is required and could not be determined for IAM policy collection.")
        if data.error_details and data.project_id == (project_id or gcp_iam_collector.get_gcp_project_id()):
            # Se o project_id não foi passado, o collector usa o do ambiente. Comparar com o resolvido.
            raise HTTPException(status_code=500, detail=data.error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP Project IAM Policy collection for project {project_id or 'default'}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_project_iam_policy_data endpoint for project {project_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Endpoints de Coleta Huawei Cloud ---
from app.huawei import huawei_obs_collector, huawei_ecs_collector, huawei_iam_collector
from app.schemas import huawei_obs, huawei_ecs, huawei_iam

HUAWEI_ROUTER_PREFIX = "/collect/huawei"

@router.get(f"{HUAWEI_ROUTER_PREFIX}/obs/buckets", response_model=List[huawei_obs.HuaweiOBSBucketData], name="huawei_collector:get_obs_buckets")
async def collect_huawei_obs_buckets_data(
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud (usado para escopo e credenciais)."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud (ex: ap-southeast-1)."),
    # current_user: Any = Depends(get_current_active_user) # Adicionar autenticação
):
    """Coleta dados de configuração de Huawei Cloud OBS buckets."""
    try:
        data = await huawei_obs_collector.get_huawei_obs_buckets(project_id=project_id, region_id=region_id)
        if data and data[0].error_details and data[0].name.startswith("ERROR_"):
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei OBS Buckets collection for project {project_id} in region {region_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_huawei_obs_buckets_data for project {project_id} in region {region_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{HUAWEI_ROUTER_PREFIX}/ecs/instances", response_model=List[huawei_ecs.HuaweiECSServerData], name="huawei_collector:get_ecs_instances")
async def collect_huawei_ecs_instances_data(
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de instâncias ECS (VMs) da Huawei Cloud."""
    try:
        data = await huawei_ecs_collector.get_huawei_ecs_instances(project_id=project_id, region_id=region_id)
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei ECS Instances collection for project {project_id} in region {region_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_huawei_ecs_instances_data for project {project_id} in region {region_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{HUAWEI_ROUTER_PREFIX}/vpc/security-groups", response_model=List[huawei_ecs.HuaweiVPCSecurityGroup], name="huawei_collector:get_vpc_sgs")
async def collect_huawei_vpc_sgs_data(
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de Security Groups VPC da Huawei Cloud."""
    try:
        # A função get_huawei_vpc_security_groups está em huawei_ecs_collector.py
        data = await huawei_ecs_collector.get_huawei_vpc_security_groups(project_id=project_id, region_id=region_id)
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei VPC SGs collection for project {project_id} in region {region_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_huawei_vpc_sgs_data for project {project_id} in region {region_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{HUAWEI_ROUTER_PREFIX}/iam/users", response_model=List[huawei_iam.HuaweiIAMUserData], name="huawei_collector:get_iam_users")
async def collect_huawei_iam_users_data(
    region_id: str = Query(..., description="ID da Região Huawei Cloud para instanciar o cliente IAM (endpoint)."),
    domain_id: Optional[str] = Query(None, description="ID do Domínio (Conta) Huawei Cloud. Se não fornecido, tenta obter do ambiente."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de usuários IAM da Huawei Cloud."""
    try:
        data = await huawei_iam_collector.get_huawei_iam_users(domain_id=domain_id, region_id=region_id)
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            if "Domain ID" in data[0].error_details: # Erro específico de configuração
                 raise HTTPException(status_code=400, detail=data[0].error_details)
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei IAM Users collection for domain {domain_id or 'default'} in region {region_id}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_huawei_iam_users_data for domain {domain_id or 'default'} in region {region_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# --- Endpoints de Coleta Azure ---
from app.azure import vm_collector as azure_vm_collector
from app.azure import storage_collector as azure_storage_collector
from app.schemas.azure import azure_compute, azure_storage

AZURE_ROUTER_PREFIX = "/collect/azure"

@router.get(f"{AZURE_ROUTER_PREFIX}/virtualmachines", response_model=List[azure_compute.AzureVirtualMachineData], name="azure_collector:get_virtual_machines")
async def collect_azure_virtual_machines_data(
    subscription_id: Optional[str] = Query(None, description="ID da Subscrição Azure. Se não fornecido, tenta obter do ambiente (AZURE_SUBSCRIPTION_ID)."),
    # current_user: Any = Depends(get_current_active_user) # Adicionar autenticação
):
    """Coleta dados de configuração de Azure Virtual Machines."""
    sub_id_to_use = subscription_id or azure_vm_collector.AZURE_SUBSCRIPTION_ID # Tenta pegar do manager se não fornecido
    if not sub_id_to_use:
        raise HTTPException(status_code=400, detail="Azure Subscription ID is required and was not provided nor found in environment.")
    try:
        data = await azure_vm_collector.get_azure_vm_data(subscription_id=sub_id_to_use)
        # Adicionar checagem de erro global similar aos outros provedores se o coletor retornar um item de erro.
        # Ex: if data and data[0].error_details and data[0].id.startswith("ERROR_"):
        #         raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Azure Virtual Machines collection for subscription {sub_id_to_use}: {http_exc.detail}")
        raise http_exc
    except ValueError as ve: # Captura ValueError do azure_client_manager se sub_id não for encontrado
        logger.error(f"ValueError during Azure Virtual Machines collection for subscription {sub_id_to_use}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in collect_azure_virtual_machines_data for subscription {sub_id_to_use}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get(f"{AZURE_ROUTER_PREFIX}/storageaccounts", response_model=List[azure_storage.AzureStorageAccountData], name="azure_collector:get_storage_accounts")
async def collect_azure_storage_accounts_data(
    subscription_id: Optional[str] = Query(None, description="ID da Subscrição Azure. Se não fornecido, tenta obter do ambiente (AZURE_SUBSCRIPTION_ID)."),
    # current_user: Any = Depends(get_current_active_user) # Adicionar autenticação
):
    """Coleta dados de configuração de Azure Storage Accounts e seus Blob Containers."""
    sub_id_to_use = subscription_id or azure_storage_collector.AZURE_SUBSCRIPTION_ID # Tenta pegar do manager se não fornecido
    if not sub_id_to_use:
        raise HTTPException(status_code=400, detail="Azure Subscription ID is required and was not provided nor found in environment.")
    try:
        data = await azure_storage_collector.get_azure_storage_account_data(subscription_id=sub_id_to_use)
        # Adicionar checagem de erro global similar
        # Ex: if data and data[0].error_details and data[0].id.startswith("ERROR_"):
        #         raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Azure Storage Accounts collection for subscription {sub_id_to_use}: {http_exc.detail}")
        raise http_exc
    except ValueError as ve: # Captura ValueError do azure_client_manager
        logger.error(f"ValueError during Azure Storage Accounts collection for subscription {sub_id_to_use}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in collect_azure_storage_accounts_data for subscription {sub_id_to_use}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
