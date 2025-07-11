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
from app.gcp import gcp_storage_collector, gcp_compute_collector, gcp_iam_collector, gke_collector
from app.schemas import gcp_storage, gcp_compute, gcp_iam # Schemas individuais
from app.schemas.gcp_gke_schemas import GKEClusterData # Schema específico para GKE
from fastapi.concurrency import run_in_threadpool # Para chamadas síncronas em GKE


# As rotas GCP já estão prefixadas com /gcp no main.py do collector service
# ao incluir este router com prefixo /collect.
# Logo, os paths aqui devem ser relativos a /gcp. Ex: /storage/buckets

@router.get("/storage/buckets", response_model=List[gcp_storage.GCPStorageBucketData], name="gcp:collect_storage_buckets")
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

@router.get("/gke/clusters", response_model=List[GKEClusterData], name="gcp:collect_gke_clusters")
async def collect_gke_clusters_data(
    project_id: Optional[str] = Query(None, description="ID do Projeto GCP. Se não fornecido, tenta obter do ambiente."),
    location: str = Query("-", description="Location (região ou zona) para listar clusters, ou '-' para todas as locations.")
):
    """Coleta dados de configuração de Google Kubernetes Engine (GKE) clusters."""
    try:
        # gke_collector.get_gke_clusters é síncrono devido à biblioteca google-cloud-container
        data = await run_in_threadpool(gke_collector.get_gke_clusters, project_id=project_id, location=location)

        if data and isinstance(data, list) and data[0].error_details and data[0].name.startswith("ERROR_"):
            if "Project ID is required" in data[0].error_details or "GCP Project ID not found" in data[0].error_details :
                 raise HTTPException(status_code=400, detail=data[0].error_details)
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GKE Clusters collection for project {project_id or 'default'}, location {location}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gke_clusters_data for project {project_id or 'default'}, location {location}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# --- Endpoints de Coleta Huawei Cloud ---
from app.huawei import huawei_obs_collector, huawei_ecs_collector, huawei_iam_collector
from app.schemas import huawei_obs, huawei_ecs, huawei_iam # Schemas já importados de app.schemas.huawei_*

# HUAWEI_ROUTER_PREFIX = "/collect/huawei"

@router.get("/huawei/obs/buckets", response_model=List[huawei_obs.HuaweiOBSBucketData], name="huawei:collect_obs_buckets")
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

from typing import Optional # Adicionado para Optional nos Query params

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
    # A lógica para obter subscription_id das settings já está no azure_client_manager e nos coletores.
    # O controller pode simplesmente passar o subscription_id se fornecido.
    # Os coletores levantarão ValueError se o ID não puder ser determinado.
    if not subscription_id and not azure_vm_collector.settings.AZURE_SUBSCRIPTION_ID:
         raise HTTPException(status_code=400, detail="Azure Subscription ID is required. Provide it as a query parameter or set AZURE_SUBSCRIPTION_ID in environment.")

    try:
        data = await azure_vm_collector.get_azure_vm_data(subscription_id=subscription_id) # Passa None se não fornecido na query
        return data
    except ValueError as ve:
        logger.error(f"Configuration error for Azure VM collection: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in collect_azure_virtual_machines_data for subscription {subscription_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get(f"{AZURE_ROUTER_PREFIX}/storageaccounts", response_model=List[azure_storage.AzureStorageAccountData], name="azure_collector:get_storage_accounts")
async def collect_azure_storage_accounts_data(
    subscription_id: Optional[str] = Query(None, description="ID da Subscrição Azure. Se não fornecido, tenta obter do ambiente (AZURE_SUBSCRIPTION_ID)."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de configuração de Azure Storage Accounts."""
    if not subscription_id and not azure_storage_collector.settings.AZURE_SUBSCRIPTION_ID:
         raise HTTPException(status_code=400, detail="Azure Subscription ID is required. Provide it as a query parameter or set AZURE_SUBSCRIPTION_ID in environment.")
    try:
        data = await azure_storage_collector.get_azure_storage_account_data(subscription_id=subscription_id)
        return data
    except ValueError as ve:
        logger.error(f"Configuration error for Azure Storage Account collection: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in collect_azure_storage_accounts_data for subscription {subscription_id or 'default'}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Endpoints de Coleta Google Workspace ---
from app.google_workspace import user_collector as gws_user_collector
from app.google_workspace import drive_collector as gws_drive_collector
from app.schemas.google_workspace import google_workspace_user, google_drive_shared_drive, google_drive_file

GWS_ROUTER_PREFIX = "/collect/googleworkspace"

@router.get(f"{GWS_ROUTER_PREFIX}/users", response_model=google_workspace_user.GoogleWorkspaceUserCollection, name="gws_collector:get_users")
async def collect_gws_users_data(
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace (e.g., 'my_customer' ou C0xxxxxxx). Default das settings se não fornecido."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado para impersonação. Default das settings se não fornecido."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de usuários do Google Workspace."""
    try:
        # A função coletora já usa os defaults das settings se os params forem None.
        # E retorna um objeto GoogleWorkspaceUserCollection que pode conter error_message.
        return await gws_user_collector.get_google_workspace_users_data(
            customer_id=customer_id,
            delegated_admin_email=delegated_admin_email
        )
    except Exception as e: # Captura exceções inesperadas antes da formação do objeto de coleção
        logger.exception(f"Unexpected error in collect_gws_users_data endpoint")
        # Retornar o schema de coleção com a mensagem de erro, se possível, ou um HTTP 500.
        # Para consistência, o coletor deve sempre retornar o schema, mesmo com erro.
        # Se a exceção for antes disso, um 500 é apropriado.
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")

@router.get(f"{GWS_ROUTER_PREFIX}/drive/shared-drives", response_model=List[google_drive_shared_drive.SharedDriveData], name="gws_collector:get_shared_drives")
async def collect_gws_shared_drives_data(
    customer_id: Optional[str] = Query(None, description="Google Workspace Customer ID."),
    delegated_admin_email: Optional[str] = Query(None, description="Delegated admin email."),
    # current_user: Any = Depends(get_current_active_user)
):
    """Coleta dados de Drives Compartilhados do Google Workspace e arquivos problematicamente compartilhados dentro deles."""
    try:
        data = await gws_drive_collector.get_google_drive_shared_drives_data(
            customer_id=customer_id,
            delegated_admin_email=delegated_admin_email
        )
        # O coletor pode retornar um item de erro na lista.
        if data and data[0].error_details and data[0].id.startswith("ERROR_"):
            # Se for um erro global retornado como o único item da lista.
            raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gws_shared_drives_data endpoint")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")

@router.get(f"{GWS_ROUTER_PREFIX}/drive/public-files", response_model=List[google_drive_file.DriveFileData], name="gws_collector:get_public_files")
async def collect_gws_public_files_data(
    customer_id: Optional[str] = Query(None, description="Google Workspace Customer ID."),
    delegated_admin_email: Optional[str] = Query(None, description="Delegated admin email."),
    # current_user: Any = Depends(get_current_active_user)
):
    """
    Coleta dados de arquivos públicos ou compartilhados por link no Google Drive (Escopo MVP pode ser limitado).
    Atualmente, esta função no coletor é mais informativa e não faz uma varredura completa.
    """
    try:
        data = await gws_drive_collector.get_google_drive_public_files_data(
            customer_id=customer_id,
            delegated_admin_email=delegated_admin_email
        )
        if data and data[0].error_details and data[0].id.startswith("INFO_") or data[0].id.startswith("ERROR_"):
            # Retorna a informação/erro como um item de dados, o frontend pode exibir isso.
            # Ou podemos decidir levantar um HTTP 501 Not Implemented se for INFO_.
            if data[0].id.startswith("INFO_"):
                 # Não é um erro, mas uma indicação de funcionalidade limitada.
                 # O frontend pode tratar isso. Ou podemos retornar um 200 com esta info.
                 pass # Deixar o response_model validar.
            elif data[0].id.startswith("ERROR_"):
                 raise HTTPException(status_code=500, detail=data[0].error_details)
        return data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gws_public_files_data endpoint")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")
