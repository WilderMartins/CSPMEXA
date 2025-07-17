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


# --- Endpoints de Coleta Microsoft 365 ---
# Importar coletores e schemas M365
from app.m365 import m365_tenant_security_collector
from app.schemas.m365 import m365_security_schemas

M365_ROUTER_PREFIX = "/collect/m365" # Ou apenas /m365 se o prefixo /collect for adicionado no main.py

@router.get(f"{M365_ROUTER_PREFIX}/users-mfa-status", response_model=m365_security_schemas.M365UserMFAStatusCollection, name="m365:collect_users_mfa_status")
async def collect_m365_users_mfa_status_data(
    # tenant_id: Optional[str] = Query(None, description="ID do Tenant M365. Se não fornecido, tenta obter das settings."),
    # A autenticação via m365_client_manager já usa o tenant_id das settings.
    # Se precisarmos suportar múltiplos tenants dinamicamente, o client_manager precisaria ser ajustado.
):
    """Coleta dados de status de MFA de usuários do Microsoft 365."""
    try:
        # O m365_tenant_security_collector usará o m365_client_manager que é configurado com Client ID, Secret e Tenant ID das settings.
        data = await m365_tenant_security_collector.get_m365_users_mfa_status()
        if data.error_message and not data.users_mfa_status: # Erro global sem nenhum dado parcial
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during M365 User MFA Status collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_m365_users_mfa_status_data endpoint")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get(f"{M365_ROUTER_PREFIX}/conditional-access-policies", response_model=m365_security_schemas.M365ConditionalAccessPolicyCollection, name="m365:collect_ca_policies")
async def collect_m365_ca_policies_data(
    # tenant_id: Optional[str] = Query(None, description="ID do Tenant M365."),
):
    """Coleta dados de Políticas de Acesso Condicional do Microsoft 365 / Azure AD."""
    try:
        data = await m365_tenant_security_collector.get_m365_conditional_access_policies()
        if data.error_message and not data.policies: # Erro global sem nenhum dado parcial
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during M365 Conditional Access Policies collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_m365_ca_policies_data endpoint")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# Adicionar imports para o novo coletor GWS Audit e seus schemas
from app.google_workspace import gws_audit_collector
from app.schemas.google_workspace import gws_audit_log_schemas
import datetime # Para os tipos de data nos query params

@router.get(f"{GWS_ROUTER_PREFIX}/auditlogs", response_model=gws_audit_log_schemas.GWSAuditLogCollection, name="gws:collect_audit_logs")
async def collect_gws_audit_logs_data(
    application_name: str = Query(..., description="Nome da aplicação para filtrar logs (ex: login, drive, admin, token)."),
    customer_id: Optional[str] = Query(None, description="ID do Cliente Google Workspace (e.g., 'my_customer' ou C0xxxxxxx)."),
    delegated_admin_email: Optional[str] = Query(None, description="E-mail do administrador delegado para impersonação."),
    max_total_results: int = Query(1000, ge=100, le=10000, description="Número máximo de logs a serem retornados."),
    start_time_iso: Optional[str] = Query(None, description="Timestamp ISO 8601 de início (UTC). Default: 24h atrás."),
    end_time_iso: Optional[str] = Query(None, description="Timestamp ISO 8601 de fim (UTC). Default: agora."),
):
    """Coleta logs de auditoria do Google Workspace para uma aplicação específica."""
    try:
        start_time_dt: Optional[datetime.datetime] = None
        end_time_dt: Optional[datetime.datetime] = None
        if start_time_iso:
            try:
                start_time_dt = datetime.datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de start_time_iso inválido. Use ISO 8601 UTC (ex: YYYY-MM-DDTHH:MM:SSZ).")
        if end_time_iso:
            try:
                end_time_dt = datetime.datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de end_time_iso inválido. Use ISO 8601 UTC.")

        # A função get_gws_audit_logs é síncrona (devido ao SDK do Google).
        # Usar run_in_threadpool.
        data = await run_in_threadpool(
            gws_audit_collector.get_gws_audit_logs,
            application_name=application_name,
            customer_id=customer_id,
            delegated_admin_email=delegated_admin_email,
            max_total_results=max_total_results,
            start_time=start_time_dt,
            end_time=end_time_dt
        )
        if data.error_message and not data.items: # Erro global sem nenhum dado parcial
            # Decidir se o erro é 4xx ou 5xx baseado na mensagem
            if "not configured" in data.error_message or "Failed to get Google Workspace service client" in data.error_message:
                 raise HTTPException(status_code=400, detail=data.error_message) # Erro de configuração
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GWS Audit Logs collection for app '{application_name}': {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gws_audit_logs_data endpoint for app '{application_name}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# Adicionar imports para o novo coletor CTS Huawei e seus schemas
from app.huawei import huawei_cts_collector
from app.schemas.huawei import huawei_cts_schemas

# Adicionar imports para o novo coletor GCP SCC e seus schemas
from app.gcp import gcp_scc_collector
from app.schemas.gcp import gcp_scc_schemas

# Adicionar imports para o novo coletor GCP CAI e seus schemas
from app.gcp import gcp_asset_inventory_collector
from app.schemas.gcp import gcp_cai_schemas

# Adicionar imports para o novo coletor GCP Cloud Audit Logs e seus schemas
from app.gcp import gcp_cloud_audit_logs_collector
from app.schemas.gcp import gcp_cloud_audit_log_schemas

# Adicionar imports para o novo coletor Huawei CSG e seus schemas
from app.huawei import huawei_csg_collector
from app.schemas.huawei import huawei_csg_schemas

# Adicionar imports para o novo coletor AWS CloudTrail e seus schemas
from app.aws import cloudtrail_collector
from app.schemas import collector_cloudtrail_schemas


@router.get("/aws/cloudtrail", response_model=List[collector_cloudtrail_schemas.CloudTrailData], name="aws:collect_cloudtrail_data")
async def collect_aws_cloudtrail_data():
    """Coleta dados de configuração do AWS CloudTrail."""
    try:
        # A função de coleta pode precisar de credenciais, que seriam obtidas de forma segura
        # e passadas para o coletor. Assumindo que o coletor lida com a obtenção de credenciais.
        data = await cloudtrail_collector.list_trails() # A função precisa ser async
        return data
    except Exception as e:
        logger.exception("Erro inesperado ao coletar dados do AWS CloudTrail.")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get(f"{HUAWEI_ROUTER_PREFIX}/cts/traces", response_model=huawei_cts_schemas.CTSTraceCollection, name="huawei:collect_cts_traces")
async def collect_huawei_cts_traces_data(
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud para escopo de recursos."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud para o endpoint do cliente CTS."),
    domain_id: Optional[str] = Query(None, description="ID do Domínio da conta Huawei Cloud para autenticação IAM."),
    tracker_name: str = Query("system", description="Nome do tracker CTS (ex: 'system' ou um nome customizado)."),
    max_total_traces: int = Query(1000, ge=10, le=10000, description="Número máximo de traces a serem retornados no total."),
    # Datas podem ser adicionadas como parâmetros se necessário para o frontend controlar o período
    # from_date: Optional[datetime.datetime] = Query(None, description="Start date for traces (ISO format)"),
    # to_date: Optional[datetime.datetime] = Query(None, description="End date for traces (ISO format)"),
):
    """Coleta traces do Cloud Trace Service (CTS) da Huawei Cloud."""
    try:
        # A função get_huawei_cts_traces é síncrona devido ao SDK da Huawei ser síncrono.
        # Precisamos rodá-la em um threadpool para não bloquear o event loop do FastAPI.
        # O run_in_threadpool é importado de fastapi.concurrency.
        # (Se não estiver, adicione: from fastapi.concurrency import run_in_threadpool)

        # Definir os parâmetros de tempo se não forem passados (ex: últimas 24h)
        # Ou deixar o coletor usar seus defaults.
        # time_to = to_date or datetime.datetime.now(datetime.timezone.utc)
        # time_from = from_date or (time_to - datetime.timedelta(days=1))

        data = await run_in_threadpool(
            huawei_cts_collector.get_huawei_cts_traces,
            project_id=project_id,
            region_id=region_id,
            domain_id=domain_id,
            tracker_name=tracker_name,
            max_total_traces=max_total_traces
            # time_from=time_from, # Passar se os query params forem adicionados
            # time_to=time_to      # Passar se os query params forem adicionados
        )
        if data.error_message and not data.traces: # Erro global sem nenhum dado parcial
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei CTS Traces collection: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("Unexpected error in collect_huawei_cts_traces_data endpoint")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/scc/findings", response_model=gcp_scc_schemas.GCPSCCFindingCollection, name="gcp:collect_scc_findings")
async def collect_gcp_scc_findings_data(
    parent_resource: str = Query(..., description="Recurso pai para listar findings (ex: 'organizations/ORG_ID/sources/-' ou 'projects/PROJECT_ID/sources/-')."),
    scc_filter: Optional[str] = Query(None, description="Filtro para a API SCC (ex: 'state=\"ACTIVE\" AND severity=\"HIGH\"')."),
    max_total_results: int = Query(1000, ge=100, le=10000, description="Número máximo de findings a serem retornados."),
):
    """Coleta findings do GCP Security Command Center."""
    try:
        # A função get_gcp_scc_findings é síncrona devido ao SDK do Google.
        # Usar run_in_threadpool.
        data = await run_in_threadpool(
            gcp_scc_collector.get_gcp_scc_findings,
            parent_resource=parent_resource,
            scc_filter=scc_filter,
            max_total_results=max_total_results
        )
        if data.error_message and not data.findings: # Erro global sem nenhum dado parcial
            if "DefaultCredentialsError" in data.error_message or "PERMISSION_DENIED" in data.error_message:
                 raise HTTPException(status_code=403, detail=data.error_message) # Erro de permissão/credencial
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP SCC Findings collection for parent '{parent_resource}': {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in collect_gcp_scc_findings_data endpoint for parent '{parent_resource}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/cai/assets", response_model=gcp_cai_schemas.GCPAssetCollection, name="gcp:list_cai_assets")
async def list_gcp_cai_assets_data(
    scope: str = Query(..., description="Escopo da consulta CAI (ex: 'projects/PROJECT_ID', 'organizations/ORG_ID')."),
    asset_types: Optional[List[str]] = Query(None, description="Lista de tipos de ativos a serem retornados (ex: ['compute.googleapis.com/Instance']). Todos se não especificado."),
    content_type: str = Query("RESOURCE", description="Tipo de conteúdo a ser retornado (RESOURCE, IAM_POLICY, etc.)."),
    max_total_results: int = Query(1000, ge=10, le=100000, description="Número máximo de ativos a serem retornados no total."),
):
    """Lista ativos do GCP Cloud Asset Inventory para um escopo e tipos de ativo específicos."""
    try:
        # A função get_gcp_cloud_assets é síncrona. Usar run_in_threadpool.
        data = await run_in_threadpool(
            gcp_asset_inventory_collector.get_gcp_cloud_assets,
            scope=scope,
            asset_types=asset_types,
            content_type=content_type,
            max_total_results=max_total_results
        )
        if data.error_message and not data.assets: # Erro global sem nenhum dado parcial
            if "DefaultCredentialsError" in data.error_message or "InvalidArgument" in data.error_message or "PERMISSION_DENIED" in data.error_message:
                 raise HTTPException(status_code=400, detail=data.error_message) # Erro de config/permissão
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP CAI Assets list for scope '{scope}': {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in list_gcp_cai_assets_data endpoint for scope '{scope}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{GCP_ROUTER_PREFIX}/auditlogs", response_model=gcp_cloud_audit_log_schemas.GCPCloudAuditLogCollection, name="gcp:list_cloud_audit_logs")
async def list_gcp_cloud_audit_logs_data(
    project_ids: List[str] = Query(..., description="Lista de IDs de Projeto GCP para consultar logs. Pode ser um único ID de projeto, ou múltiplos para consulta mais ampla se suportado pelo backend (ex: via organização)."),
    log_filter: Optional[str] = Query(None, description="Filtro avançado para a API de Logging do GCP (ex: 'protoPayload.methodName=\"storage.objects.delete\"')."),
    max_total_results: int = Query(1000, ge=10, le=50000, description="Número máximo de entradas de log a serem retornadas."),
    # Adicionar start_time, end_time se o frontend precisar controlar isso finamente.
    # O coletor atual usa defaults (últimas 24h) se não passados.
):
    """Lista entradas de log do GCP Cloud Logging, com foco em Audit Logs."""
    try:
        # A função get_gcp_cloud_audit_logs é síncrona. Usar run_in_threadpool.
        data = await run_in_threadpool(
            gcp_cloud_audit_logs_collector.get_gcp_cloud_audit_logs,
            project_ids=project_ids, # Passando a lista de project_ids
            log_filter=log_filter,
            max_total_results=max_total_results
        )
        if data.error_message and not data.entries: # Erro global sem nenhum dado parcial
            if "DefaultCredentialsError" in data.error_message or "InvalidArgument" in data.error_message or "PERMISSION_DENIED" in data.error_message:
                 raise HTTPException(status_code=400, detail=data.error_message)
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during GCP Cloud Audit Logs list for projects '{project_ids}': {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in list_gcp_cloud_audit_logs_data endpoint for projects '{project_ids}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get(f"{HUAWEI_ROUTER_PREFIX}/csg/risks", response_model=huawei_csg_schemas.CSGRiskCollection, name="huawei:list_csg_risks")
async def list_huawei_csg_risks_data(
    project_id: str = Query(..., description="ID do Projeto Huawei Cloud para escopo de recursos."),
    region_id: str = Query(..., description="ID da Região Huawei Cloud para o endpoint do cliente CSG."),
    domain_id: Optional[str] = Query(None, description="ID do Domínio da conta Huawei Cloud para autenticação IAM."),
    max_total_results: int = Query(1000, ge=10, le=10000, description="Número máximo de riscos a serem retornados."),
    # Adicionar mais Query Params para filtros específicos do CSG se necessário
):
    """Lista riscos de segurança do Huawei Cloud Security Guard (CSG)."""
    try:
        # A função get_huawei_csg_risks é síncrona. Usar run_in_threadpool.
        data = await run_in_threadpool(
            huawei_csg_collector.get_huawei_csg_risks,
            project_id=project_id,
            region_id=region_id,
            domain_id=domain_id,
            max_total_results=max_total_results
        )
        if data.error_message and not data.risks: # Erro global sem nenhum dado parcial
            if "credentials" in data.error_message.lower() or "configured" in data.error_message.lower():
                 raise HTTPException(status_code=400, detail=data.error_message) # Erro de config/permissão
            raise HTTPException(status_code=500, detail=data.error_message)
        return data
    except HTTPException as http_exc:
        logger.error(f"HTTPException during Huawei CSG Risks list for project '{project_id}', region '{region_id}': {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in list_huawei_csg_risks_data endpoint for project '{project_id}', region '{region_id}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
