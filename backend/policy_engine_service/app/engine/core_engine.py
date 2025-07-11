from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import (
    AnalysisRequest,
    S3BucketDataInput, EC2InstanceDataInput, EC2SecurityGroupDataInput, IAMUserDataInput,
    GCPStorageBucketDataInput, GCPComputeInstanceDataInput, GCPFirewallDataInput, GCPProjectIAMPolicyDataInput,
    HuaweiOBSBucketDataInput, HuaweiECSServerDataInput, HuaweiVPCSecurityGroupInput, HuaweiIAMUserDataInput,
    AzureVirtualMachineDataInput, AzureStorageAccountDataInput,
    GoogleWorkspaceUserDataInput # Google Workspace Inputs
)
from app.schemas.alert_schema import Alert
from app.engine import aws_s3_policies, aws_ec2_policies, aws_iam_policies
from app.engine import gcp_storage_policies, gcp_compute_policies, gcp_iam_policies
from app.engine import huawei_obs_policies, huawei_ecs_policies, huawei_iam_policies
from app.engine import azure_vm_policies, azure_storage_policies
from app.engine import google_workspace_user_policies, google_workspace_drive_policies # Google Workspace Policies
import logging

logger = logging.getLogger(__name__)
# Helper para garantir que os tipos de dados para IAMRoleDataInput e IAMPolicyDataInput existam
# (se não foram definidos completamente em input_data_schema.py, isso evitará NameError)
try:
    from app.schemas.input_data_schema import IAMRoleDataInput, IAMPolicyDataInput
except ImportError:
    IAMRoleDataInput = dict # Fallback
    IAMPolicyDataInput = dict # Fallback

# from app.db.session import SessionLocal # Não mais necessário aqui, o CRUD lida com a sessão.
# from app.crud.crud_alert import alert_crud # Importa a instância do CRUD.
# O controller /analyze agora passa a sessão do DB para o CRUD.
# O PolicyEngine em si não precisa mais interagir diretamente com o DB.
# Ele apenas gera os dados para os alertas.

class PolicyEngine:
    def __init__(self):
        # No futuro, poderíamos carregar configurações de políticas, pesos, etc.
        pass

    # def _get_db(self): # Removido, o controller gerencia a sessão do DB
    #     """Helper para obter uma sessão de banco de dados."""
    #     return SessionLocal()

    async def analyze(self, request_data: AnalysisRequest) -> List[Dict[str, Any]]: # Retorna List[Dict] para AlertCreate
        """
        Ponto de entrada principal para analisar os dados de recursos da nuvem.
        Direciona os dados para os módulos de avaliação de políticas apropriados.
        Retorna uma lista de dicionários, cada um correspondendo aos dados necessários para criar um AlertCreate.
        A persistência será feita pelo controller/CRUD.
        """
        # Alterado: generated_alerts_schemas para generated_alert_data_list
        generated_alert_data_list: List[Dict[str, Any]] = []

        provider = request_data.provider.lower()
        service = request_data.service.lower()
        data = request_data.data
        account_id = request_data.account_id

        if not data:
            logger.info(f"No data provided for provider '{provider}', service '{service}'. Skipping analysis.")
            return []

        logger.info(f"Starting analysis for provider: {provider}, service: {service}, account: {account_id or 'N/A'}")

        if provider == "aws":
            if service == "s3":
                s3_alerts_data = aws_s3_policies.evaluate_s3_policies(
                    s3_buckets_data=data, # type: ignore
                    account_id=account_id
                )
                generated_alert_data_list.extend(s3_alerts_data)

            elif service == "ec2_instances":
                # Assume que data é List[EC2InstanceDataInput]
                # Adicionar type checking se necessário
                ec2_instance_alerts_data = aws_ec2_policies.evaluate_ec2_instance_policies(
                     instances_data=data, # type: ignore
                     account_id=account_id
                )
                generated_alert_data_list.extend(ec2_instance_alerts_data)

            elif service == "ec2_security_groups":
                if not all(isinstance(item, EC2SecurityGroupDataInput) for item in data): # type: ignore
                     logger.error("Data for ec2_security_groups is not of type List[EC2SecurityGroupDataInput]. Skipping.")
                else:
                    sgs_by_region_map: Dict[str, List[EC2SecurityGroupDataInput]] = {}
                    for sg_input_item in data:
                        sg_region = sg_input_item.region if hasattr(sg_input_item, 'region') and sg_input_item.region else 'unknown_region_sg'
                        sgs_by_region_map.setdefault(sg_region, []).append(sg_input_item)

                    for reg, sgs_list in sgs_by_region_map.items():
                        sg_alerts_data = aws_ec2_policies.evaluate_ec2_sg_policies(
                            security_groups_data=sgs_list,
                            account_id=account_id,
                            region=reg
                        )
                        generated_alert_data_list.extend(sg_alerts_data)

            elif service == "iam_users":
                iam_user_alerts_data = aws_iam_policies.evaluate_iam_user_policies(
                    users_data=data, # type: ignore
                    account_id=account_id
                )
                generated_alert_data_list.extend(iam_user_alerts_data)
            else:
                logger.warning(f"Unsupported AWS service for analysis: {service}")

        elif provider == "gcp":
            if service == "gcp_storage_buckets":
                if not all(isinstance(item, GCPStorageBucketDataInput) for item in data):
                    logger.error("Data for gcp_storage_buckets is not List[GCPStorageBucketDataInput]. Skipping.")
                else:
                    storage_alerts_data = gcp_storage_policies.evaluate_gcp_storage_policies(
                        gcp_buckets_data=data,
                        project_id=account_id
                    )
                    generated_alert_data_list.extend(storage_alerts_data)
            elif service == "gcp_compute_instances":
                if not all(isinstance(item, GCPComputeInstanceDataInput) for item in data):
                    logger.error("Data for gcp_compute_instances is not List[GCPComputeInstanceDataInput]. Skipping.")
                else:
                    instance_alerts_data = gcp_compute_policies.evaluate_gcp_compute_instance_policies(
                        instances_data=data,
                        project_id=account_id
                    )
                    generated_alert_data_list.extend(instance_alerts_data)
            elif service == "gcp_compute_firewalls":
                if not all(isinstance(item, GCPFirewallDataInput) for item in data):
                    logger.error("Data for gcp_compute_firewalls is not List[GCPFirewallDataInput]. Skipping.")
                else:
                    firewall_alerts_data = gcp_compute_policies.evaluate_gcp_firewall_policies(
                        firewalls_data=data,
                        project_id=account_id
                    )
                    generated_alert_data_list.extend(firewall_alerts_data)
            elif service == "gcp_iam_project_policies":
                if data is not None and not isinstance(data, GCPProjectIAMPolicyDataInput):
                     logger.error("Data for gcp_iam_project_policies is not GCPProjectIAMPolicyDataInput. Skipping.")
                else:
                    iam_alerts_data = gcp_iam_policies.evaluate_gcp_project_iam_policies(
                        project_iam_data=data,
                        project_id=account_id
                    )
                    generated_alert_data_list.extend(iam_alerts_data)
            elif service == "gke_clusters": # Novo para GKE
                if not all(isinstance(item, GKEClusterDataInput) for item in data):
                    logger.error(f"Data for GCP GKE service is not List[GKEClusterDataInput]. Skipping. Data type: {type(data[0]) if data else 'empty'}")
                else:
                    gke_alerts_data = gcp_gke_policies.evaluate_gke_policies(
                        gke_clusters_data=data,
                        project_id=account_id
                    )
                    generated_alert_data_list.extend(gke_alerts_data)
            else:
                logger.warning(f"Unsupported GCP service for analysis: {service}")

        elif provider == "huawei":
            if service == "huawei_obs_buckets":
                if not all(isinstance(item, HuaweiOBSBucketDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_obs_buckets is not List[HuaweiOBSBucketDataInput]. Skipping.")
                else:
                    obs_alerts_data = huawei_obs_policies.evaluate_huawei_obs_policies(
                        huawei_buckets_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(obs_alerts_data)
            elif service == "huawei_ecs_instances":
                if not all(isinstance(item, HuaweiECSServerDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_ecs_instances is not List[HuaweiECSServerDataInput]. Skipping.")
                else:
                    ecs_alerts_data = huawei_ecs_policies.evaluate_huawei_ecs_instance_policies(
                        instances_data=data, # type: ignore
                        account_id=account_id,
                        region_id=getattr(data[0], 'region_id', None) if data else None
                    )
                    generated_alert_data_list.extend(ecs_alerts_data)
            elif service == "huawei_vpc_security_groups":
                if not all(isinstance(item, HuaweiVPCSecurityGroupInput) for item in data): # type: ignore
                    logger.error("Data for huawei_vpc_security_groups is not List[HuaweiVPCSecurityGroupInput]. Skipping.")
                else:
                    sg_alerts_data = huawei_ecs_policies.evaluate_huawei_vpc_sg_policies(
                        sgs_data=data, # type: ignore
                        account_id=account_id,
                        region_id=getattr(data[0], 'region_id', None) if data else None
                    )
                    generated_alert_data_list.extend(sg_alerts_data)
            elif service == "huawei_iam_users":
                if not all(isinstance(item, HuaweiIAMUserDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_iam_users is not List[HuaweiIAMUserDataInput]. Skipping.")
                else:
                    iam_user_alerts_data = huawei_iam_policies.evaluate_huawei_iam_user_policies(
                        users_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(iam_user_alerts_data)
            else:
                logger.warning(f"Unsupported Huawei Cloud service for analysis: {service}")

        elif provider == "azure":
            if service == "azure_virtual_machines":
                if not all(isinstance(item, AzureVirtualMachineDataInput) for item in data): # type: ignore
                    logger.error("Data for azure_virtual_machines is not List[AzureVirtualMachineDataInput]. Skipping.")
                else:
                    vm_alerts_data = azure_vm_policies.evaluate_azure_vm_policies(
                        azure_vms_data=data, # type: ignore
                        subscription_id=account_id
                    )
                    generated_alert_data_list.extend(vm_alerts_data)
            elif service == "azure_storage_accounts":
                if not all(isinstance(item, AzureStorageAccountDataInput) for item in data): # type: ignore
                    logger.error("Data for azure_storage_accounts is not List[AzureStorageAccountDataInput]. Skipping.")
                else:
                    storage_alerts_data = azure_storage_policies.evaluate_azure_storage_policies(
                        azure_storage_accounts_data=data, # type: ignore
                        subscription_id=account_id
                    )
                    generated_alert_data_list.extend(storage_alerts_data)
            else:
                logger.warning(f"Unsupported Azure service for analysis: {service}")

        elif provider == "google_workspace":
            if service == "google_workspace_users":
                if not all(isinstance(item, GoogleWorkspaceUserDataInput) for item in data): # type: ignore
                    logger.error("Data for google_workspace_users is not List[GoogleWorkspaceUserDataInput]. Skipping.")
                else:
                    gw_user_alerts_data = google_workspace_user_policies.evaluate_google_workspace_user_policies(
                        users_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(gw_user_alerts_data)
            elif service == "google_drive_shared_drives":
                drive_alerts_data = google_workspace_drive_policies.evaluate_google_workspace_drive_policies(
                    shared_drives_data=data, # type: ignore
                    account_id=account_id
                )
                generated_alert_data_list.extend(drive_alerts_data)
            else:
                logger.warning(f"Unsupported Google Workspace service for analysis: {service}")
        else:
            logger.warning(f"Unsupported provider for analysis: {provider}")

        # A persistência foi movida para o controller/CRUD.
        # O motor agora apenas retorna a lista de dicionários de dados de alerta.
        # Cada dicionário em generated_alert_data_list deve ser compatível com AlertCreate.

        # Garantir que todos os dicionários retornados tenham os campos esperados por AlertCreate
        # e que o 'provider' esteja correto.
        final_alert_data_list = []
        for alert_dict in generated_alert_data_list:
            alert_dict["provider"] = provider # Sobrescreve ou adiciona o provider
            alert_dict.setdefault("account_id", account_id) # Garante account_id
            # Adicionar outras verificações ou transformações se necessário
            final_alert_data_list.append(alert_dict)

        logger.info(f"Analysis complete for {provider}/{service} (Account: {account_id or 'N/A'}). Generated {len(final_alert_data_list)} alert data entries.")
        return final_alert_data_list

# Instância global do motor
policy_engine = PolicyEngine()

# Adicionar import de uuid no início do arquivo, se não estiver lá
import uuid

# Importar o novo módulo de políticas RDS e o schema de input RDS
from app.engine import aws_rds_policies
from app.schemas.aws.rds_input_schema import RDSInstanceDataInput

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado
