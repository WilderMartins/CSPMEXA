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
            elif service == "iam_roles": # Novo serviço para Roles IAM
                if not all(isinstance(item, IAMRoleDataInput) for item in data): # type: ignore
                    logger.error("Data for iam_roles is not List[IAMRoleDataInput]. Skipping.")
                else:
                    iam_role_alerts_data = aws_iam_policies.evaluate_iam_role_policies(
                        roles_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(iam_role_alerts_data)
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
            elif service == "gcp_scc_findings": # Novo para GCP SCC Findings
                if not isinstance(data, GCPSCCFindingCollectionInput): # type: ignore
                    logger.error(f"Data for GCP SCC Findings is not of type GCPSCCFindingCollectionInput. Skipping. Data: {type(data)}")
                else:
                    scc_alerts_data = gcp_scc_processing.process_gcp_scc_findings(
                        scc_finding_collection=data, # type: ignore
                        gcp_parent_resource_id=account_id # account_id aqui é o parent_resource (org/folder/project)
                    )
                    generated_alert_data_list.extend(scc_alerts_data)
            elif service == "gcp_cloud_asset_inventory": # Novo para GCP CAI
                if not isinstance(data, GCPAssetCollectionInput): # type: ignore
                    logger.error(f"Data for GCP CAI is not of type GCPAssetCollectionInput. Skipping. Data: {type(data)}")
                else:
                    cai_alerts_data = gcp_cai_policies.evaluate_gcp_cai_policies(
                        asset_collection=data, # type: ignore
                        account_id=account_id # account_id aqui é o escopo da consulta (project/folder/org)
                    )
                    generated_alert_data_list.extend(cai_alerts_data)
            elif service == "gcp_cloud_audit_logs": # Novo para GCP Cloud Audit Logs
                if not isinstance(data, GCPCloudAuditLogCollectionInput): # type: ignore
                    logger.error(f"Data for GCP Cloud Audit Logs is not of type GCPCloudAuditLogCollectionInput. Skipping. Data: {type(data)}")
                else:
                    audit_log_alerts_data = gcp_cloud_audit_policies.evaluate_gcp_cloud_audit_log_policies(
                        log_collection=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(audit_log_alerts_data)
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
            elif service == "huawei_cts_logs": # Novo serviço para logs CTS
                if not isinstance(data, CTSTraceCollectionInput): # type: ignore
                    logger.error(f"Data for Huawei CTS logs is not of type CTSTraceCollectionInput. Data type: {type(data)}. Skipping.")
                else:
                    cts_alerts_data = huawei_cts_policies.evaluate_huawei_cts_policies(
                        cts_trace_collection=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(cts_alerts_data)
            elif service == "huawei_csg_risks": # Novo serviço para Riscos CSG
                if not isinstance(data, CSGRiskCollectionInput): # type: ignore
                    logger.error(f"Data for Huawei CSG Risks is not of type CSGRiskCollectionInput. Skipping. Data: {type(data)}")
                else:
                    csg_alerts_data = huawei_csg_policies.evaluate_huawei_csg_policies(
                        csg_risk_collection=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(csg_alerts_data)
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
            elif service.startswith("gws_audit_logs_"): # Novo para GWS Audit Logs
                app_name_extracted = service.replace("gws_audit_logs_", "")
                if not isinstance(data, GWSAuditLogCollectionInput): # type: ignore
                    logger.error(f"Data for GWS Audit Logs ({app_name_extracted}) is not of type GWSAuditLogCollectionInput. Skipping.")
                else:
                    # Garantir que o application_name_queried no payload seja consistente, se necessário
                    if not data.application_name_queried or data.application_name_queried != app_name_extracted:
                        logger.warning(f"Service name implies app '{app_name_extracted}' but payload reports '{data.application_name_queried}'. Using '{app_name_extracted}'.")
                        data.application_name_queried = app_name_extracted # Forçar consistência

                    gws_audit_alerts_data = gws_audit_policies.evaluate_gws_audit_log_policies(
                        gws_log_collection=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alert_data_list.extend(gws_audit_alerts_data)
            else:
                logger.warning(f"Unsupported Google Workspace service for analysis: {service}")

        elif provider == "microsoft365":
            # account_id para M365 é geralmente o Tenant ID
            tenant_id = account_id

            # Para M365, podemos ter um único payload com múltiplos tipos de dados
            # ou o API Gateway pode chamar o /analyze com um 'service' específico.
            # Vamos assumir que o 'data' pode conter chaves para cada tipo de dado coletado.
            # Ex: request_data.data = {"users_mfa_status": ..., "conditional_access_policies": ...}
            # Ou, se o 'service' especifica qual parte dos dados usar:

            mfa_input_data: Optional[M365UserMFAStatusCollectionInput] = None
            ca_policy_input_data: Optional[M365ConditionalAccessPolicyCollectionInput] = None

            if service == "m365_users_mfa_status":
                if not isinstance(data, M365UserMFAStatusCollectionInput): # type: ignore
                    logger.error(f"Data for M365 MFA status is not of type M365UserMFAStatusCollectionInput. Data: {type(data)}. Skipping.")
                else:
                    mfa_input_data = data # type: ignore
            elif service == "m365_conditional_access_policies":
                if not isinstance(data, M365ConditionalAccessPolicyCollectionInput): # type: ignore
                    logger.error(f"Data for M365 CA policies is not of type M365ConditionalAccessPolicyCollectionInput. Data: {type(data)}. Skipping.")
                else:
                    ca_policy_input_data = data # type: ignore
            elif service == "m365_tenant_security": # Um serviço "agregado"
                 # Tentar extrair os dados relevantes do payload 'data' que pode ser um dict
                if isinstance(data, dict):
                    mfa_payload = data.get("users_mfa_status")
                    if mfa_payload:
                        try:
                            mfa_input_data = M365UserMFAStatusCollectionInput(**mfa_payload)
                        except Exception as e_mfa:
                            logger.error(f"Error parsing M365 MFA data for aggregated service: {e_mfa}")

                    ca_payload = data.get("conditional_access_policies")
                    if ca_payload:
                        try:
                            ca_policy_input_data = M365ConditionalAccessPolicyCollectionInput(**ca_payload)
                        except Exception as e_ca:
                            logger.error(f"Error parsing M365 CA policy data for aggregated service: {e_ca}")
                else:
                    logger.error(f"Data for aggregated M365 service '{service}' is not a dict. Skipping.")
            else:
                logger.warning(f"Unsupported Microsoft 365 service for analysis: {service}")

            # Chamar a função de avaliação principal do m365_policies, passando os dados que temos.
            # A função evaluate_m365_policies precisará lidar com dados potencialmente None.
            if mfa_input_data or ca_policy_input_data: # Só chamar se tivermos algum dado
                m365_alerts_data = m365_policies.evaluate_m365_policies(
                    mfa_data=mfa_input_data,
                    ca_policy_data=ca_policy_input_data,
                    tenant_id=tenant_id
                )
                generated_alert_data_list.extend(m365_alerts_data)
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

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar módulos de políticas e schemas de input para Huawei CTS
from app.engine import huawei_cts_policies
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput

# Importar módulos de políticas e schemas de input para Google Workspace Audit Logs
from app.engine import gws_audit_policies
from app.schemas.google_workspace.gws_audit_input_schemas import GWSAuditLogCollectionInput

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar módulos de políticas e schemas de input para Huawei CTS
from app.engine import huawei_cts_policies
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput

# Importar módulos de políticas e schemas de input para Google Workspace Audit Logs
from app.engine import gws_audit_policies
from app.schemas.google_workspace.gws_audit_input_schemas import GWSAuditLogCollectionInput

# Importar módulos de processamento e schemas de input para GCP SCC Findings
from app.engine import gcp_scc_processing
from app.schemas.gcp.gcp_scc_input_schemas import GCPSCCFindingCollectionInput

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar módulos de políticas e schemas de input para Huawei CTS
from app.engine import huawei_cts_policies
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput

# Importar módulos de políticas e schemas de input para Google Workspace Audit Logs
from app.engine import gws_audit_policies
from app.schemas.google_workspace.gws_audit_input_schemas import GWSAuditLogCollectionInput

# Importar módulos de processamento e schemas de input para GCP SCC Findings
from app.engine import gcp_scc_processing
from app.schemas.gcp.gcp_scc_input_schemas import GCPSCCFindingCollectionInput

# Importar módulos de políticas e schemas de input para GCP Cloud Asset Inventory
from app.engine import gcp_cai_policies
from app.schemas.gcp.gcp_cai_input_schemas import GCPAssetCollectionInput

# Importar o novo módulo de políticas GKE e o schema de input GKE
from app.engine import gcp_gke_policies # Adicionado
from app.schemas.gcp.gke_input_schema import GKEClusterDataInput # Adicionado

# Importar módulos de políticas e schemas de input para Microsoft 365
from app.engine import m365_policies
from app.schemas.m365.m365_input_schemas import (
    M365UserMFAStatusCollectionInput,
    M365ConditionalAccessPolicyCollectionInput
)

# Importar módulos de políticas e schemas de input para Huawei CTS
from app.engine import huawei_cts_policies
from app.schemas.huawei.huawei_cts_input_schemas import CTSTraceCollectionInput

# Importar módulos de políticas e schemas de input para Google Workspace Audit Logs
from app.engine import gws_audit_policies
from app.schemas.google_workspace.gws_audit_input_schemas import GWSAuditLogCollectionInput

# Importar módulos de processamento e schemas de input para GCP SCC Findings
from app.engine import gcp_scc_processing
from app.schemas.gcp.gcp_scc_input_schemas import GCPSCCFindingCollectionInput

# Importar módulos de políticas e schemas de input para GCP Cloud Asset Inventory
from app.engine import gcp_cai_policies
from app.schemas.gcp.gcp_cai_input_schemas import GCPAssetCollectionInput

# Importar módulos de políticas e schemas de input para GCP Cloud Audit Logs
from app.engine import gcp_cloud_audit_policies
from app.schemas.gcp.gcp_cloud_audit_input_schemas import GCPCloudAuditLogCollectionInput

# Importar módulos de políticas e schemas de input para Huawei CSG
from app.engine import huawei_csg_policies # Adicionado
from app.schemas.huawei.huawei_csg_input_schemas import CSGRiskCollectionInput # Adicionado
