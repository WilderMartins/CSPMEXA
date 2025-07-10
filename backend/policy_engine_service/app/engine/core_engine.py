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
from app.engine import google_workspace_user_policies # Google Workspace Policies
import logging

logger = logging.getLogger(__name__)
# Helper para garantir que os tipos de dados para IAMRoleDataInput e IAMPolicyDataInput existam
# (se não foram definidos completamente em input_data_schema.py, isso evitará NameError)
try:
    from app.schemas.input_data_schema import IAMRoleDataInput, IAMPolicyDataInput
except ImportError:
    IAMRoleDataInput = dict # Fallback
    IAMPolicyDataInput = dict # Fallback

class PolicyEngine:
    def __init__(self):
        # No futuro, poderíamos carregar configurações de políticas, pesos, etc.
        pass

from app.db.session import SessionLocal # Para criar uma sessão de DB
from app.crud.crud_alert import create_alert as crud_create_alert # Função CRUD

class PolicyEngine:
    def __init__(self):
        # No futuro, poderíamos carregar configurações de políticas, pesos, etc.
        pass

    def _get_db(self):
        """Helper para obter uma sessão de banco de dados."""
        return SessionLocal()

    def analyze(self, request_data: AnalysisRequest) -> List[Alert]:
        """
        Ponto de entrada principal para analisar os dados de recursos da nuvem.
        Direciona os dados para os módulos de avaliação de políticas apropriados e persiste os alertas.
        """
        generated_alerts_schemas: List[Alert] = [] # Lista de schemas Pydantic de alertas

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
                s3_alerts = aws_s3_policies.evaluate_s3_policies(
                    s3_buckets_data=data, # type: ignore
                    account_id=account_id
                )
                generated_alerts_schemas.extend(s3_alerts)

            elif service == "ec2_instances":
                # Removida linha duplicada: alerts.extend(ec2_instance_alerts)
                # Esta seção é para 'ec2_instances', a próxima é para 'ec2_security_groups'
                generated_alerts_schemas.extend(ec2_instance_alerts)

            # Correção: Removida a duplicata da seção ec2_security_groups que chamava evaluate_ec2_instance_policies
            # A seção correta para ec2_security_groups já existe abaixo e está correta.
            # elif service == "ec2_security_groups":
            #     # A lógica original parecia ter uma cópia da avaliação de ec2_instances aqui.
            #     # Corrigido para avaliar security groups.
            #     # ec2_instance_alerts = aws_ec2_policies.evaluate_ec2_instance_policies( # Linha incorreta removida
            #         instances_data=data, # type: ignore
            #         account_id=account_id
            #     )
            #     generated_alerts_schemas.extend(ec2_instance_alerts)

            elif service == "ec2_security_groups": # Esta é a seção correta que já existia.
                if not all(isinstance(item, EC2SecurityGroupDataInput) for item in data): # type: ignore
                     logger.error("Data for ec2_security_groups is not of type List[EC2SecurityGroupDataInput]. Skipping.")
                else:
                    sgs_by_region_map: Dict[str, List[EC2SecurityGroupDataInput]] = {}
                    for sg_input_item in data: # data é List[EC2SecurityGroupDataInput]
                        sg_region = sg_input_item.region if hasattr(sg_input_item, 'region') and sg_input_item.region else 'unknown_region_sg'
                        if sg_region not in sgs_by_region_map:
                            sgs_by_region_map[sg_region] = []
                        sgs_by_region_map[sg_region].append(sg_input_item)

                    for reg, sgs_list in sgs_by_region_map.items():
                        if reg == 'unknown_region_sg':
                            logger.warning("Processing EC2 Security Groups with an undetermined region for persistence.")
                        sg_alerts = aws_ec2_policies.evaluate_ec2_sg_policies(
                            security_groups_data=sgs_list,
                            account_id=account_id,
                            region=reg
                        )
                        generated_alerts_schemas.extend(sg_alerts)

            elif service == "iam_users":
                iam_user_alerts = aws_iam_policies.evaluate_iam_user_policies(
                    users_data=data, # type: ignore
                    account_id=account_id
                )
                generated_alerts_schemas.extend(iam_user_alerts)
            # ... (outros serviços AWS) ...
            else:
                logger.warning(f"Unsupported AWS service for analysis: {service}")

        elif provider == "gcp":
            if service == "gcp_storage_buckets":
                if not all(isinstance(item, GCPStorageBucketDataInput) for item in data): # type: ignore
                    logger.error("Data for gcp_storage_buckets is not List[GCPStorageBucketDataInput]. Skipping.")
                else:
                    storage_alerts = gcp_storage_policies.evaluate_gcp_storage_policies(
                        gcp_buckets_data=data, # type: ignore
                        project_id=account_id
                    )
                    generated_alerts_schemas.extend(storage_alerts)
            # ... (outros serviços GCP) ...
            elif service == "gcp_compute_instances":
                if not all(isinstance(item, GCPComputeInstanceDataInput) for item in data): # type: ignore
                    logger.error("Data for gcp_compute_instances is not List[GCPComputeInstanceDataInput]. Skipping.")
                else:
                    instance_alerts = gcp_compute_policies.evaluate_gcp_compute_instance_policies(
                        instances_data=data, # type: ignore
                        project_id=account_id
                    )
                    generated_alerts_schemas.extend(instance_alerts)
            elif service == "gcp_compute_firewalls":
                if not all(isinstance(item, GCPFirewallDataInput) for item in data): # type: ignore
                    logger.error("Data for gcp_compute_firewalls is not List[GCPFirewallDataInput]. Skipping.")
                else:
                    firewall_alerts = gcp_compute_policies.evaluate_gcp_firewall_policies(
                        firewalls_data=data, # type: ignore
                        project_id=account_id
                    )
                    generated_alerts_schemas.extend(firewall_alerts)
            elif service == "gcp_iam_project_policies":
                if data is not None and not isinstance(data, GCPProjectIAMPolicyDataInput): # type: ignore
                     logger.error("Data for gcp_iam_project_policies is not GCPProjectIAMPolicyDataInput. Skipping.")
                else:
                    iam_alerts = gcp_iam_policies.evaluate_gcp_project_iam_policies(
                        project_iam_data=data, # type: ignore
                        project_id=account_id
                    )
                    generated_alerts_schemas.extend(iam_alerts)
            else:
                logger.warning(f"Unsupported GCP service for analysis: {service}")

        elif provider == "huawei":
            if service == "huawei_obs_buckets":
                if not all(isinstance(item, HuaweiOBSBucketDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_obs_buckets is not List[HuaweiOBSBucketDataInput]. Skipping.")
                else:
                    obs_alerts = huawei_obs_policies.evaluate_huawei_obs_policies(
                        huawei_buckets_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alerts_schemas.extend(obs_alerts)
            # ... (outros serviços Huawei) ...
            elif service == "huawei_ecs_instances":
                if not all(isinstance(item, HuaweiECSServerDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_ecs_instances is not List[HuaweiECSServerDataInput]. Skipping.")
                else:
                    ecs_alerts = huawei_ecs_policies.evaluate_huawei_ecs_instance_policies(
                        instances_data=data, # type: ignore
                        account_id=account_id,
                        region_id=getattr(data[0], 'region_id', None) if data else None
                    )
                    generated_alerts_schemas.extend(ecs_alerts)
            elif service == "huawei_vpc_security_groups":
                if not all(isinstance(item, HuaweiVPCSecurityGroupInput) for item in data): # type: ignore
                    logger.error("Data for huawei_vpc_security_groups is not List[HuaweiVPCSecurityGroupInput]. Skipping.")
                else:
                    sg_alerts = huawei_ecs_policies.evaluate_huawei_vpc_sg_policies(
                        sgs_data=data, # type: ignore
                        account_id=account_id,
                        region_id=getattr(data[0], 'region_id', None) if data else None
                    )
                    generated_alerts_schemas.extend(sg_alerts)
            elif service == "huawei_iam_users":
                if not all(isinstance(item, HuaweiIAMUserDataInput) for item in data): # type: ignore
                    logger.error("Data for huawei_iam_users is not List[HuaweiIAMUserDataInput]. Skipping.")
                else:
                    iam_user_alerts = huawei_iam_policies.evaluate_huawei_iam_user_policies(
                        users_data=data, # type: ignore
                        account_id=account_id
                    )
                    generated_alerts_schemas.extend(iam_user_alerts)
            else:
                logger.warning(f"Unsupported Huawei Cloud service for analysis: {service}")

        elif provider == "azure":
            if service == "azure_virtual_machines":
                if not all(isinstance(item, AzureVirtualMachineDataInput) for item in data): # type: ignore
                    logger.error("Data for azure_virtual_machines is not List[AzureVirtualMachineDataInput]. Skipping.")
                else:
                    vm_alerts = azure_vm_policies.evaluate_azure_vm_policies(
                        vms_data=data, # type: ignore
                        account_id=account_id # subscription_id
                    )
                    generated_alerts_schemas.extend(vm_alerts)
            elif service == "azure_storage_accounts":
                if not all(isinstance(item, AzureStorageAccountDataInput) for item in data): # type: ignore
                    logger.error("Data for azure_storage_accounts is not List[AzureStorageAccountDataInput]. Skipping.")
                else:
                    storage_alerts = azure_storage_policies.evaluate_azure_storage_policies(
                        storage_accounts_data=data, # type: ignore
                        account_id=account_id # subscription_id
                    )
                    generated_alerts_schemas.extend(storage_alerts)
            else:
                logger.warning(f"Unsupported Azure service for analysis: {service}")

        elif provider == "google_workspace":
            if service == "google_workspace_users":
                if not all(isinstance(item, GoogleWorkspaceUserDataInput) for item in data): # type: ignore
                    logger.error("Data for google_workspace_users is not List[GoogleWorkspaceUserDataInput]. Skipping.")
                else:
                    gw_user_alerts = google_workspace_user_policies.evaluate_google_workspace_user_policies(
                        users_data=data, # type: ignore
                        account_id=account_id # customer_id
                    )
                    generated_alerts_schemas.extend(gw_user_alerts)
            # Adicionar outros serviços do Google Workspace aqui (Drive, Gmail, etc.)
            else:
                logger.warning(f"Unsupported Google Workspace service for analysis: {service}")
        else:
            logger.warning(f"Unsupported provider for analysis: {provider}")

        # Persistir alertas gerados
        if generated_alerts_schemas:
            db = self._get_db()
            try:
                for alert_schema in generated_alerts_schemas:
                    # Garantir que o ID seja gerado se não estiver presente (Pydantic default pode não ser usado aqui)
                    if alert_schema.id is None:
                        alert_schema.id = str(uuid.uuid4())

                    # Garantir que created_at e updated_at sejam definidos
                    # O schema Pydantic Alert já tem defaults com datetime.now(datetime.timezone.utc)
                    # mas o modelo SQLAlchemy também tem defaults.
                    # Se o schema Pydantic já os preencheu, eles serão usados.
                    # Se não, o modelo SQLAlchemy os preencherá.

                    crud_create_alert(db=db, alert_in=alert_schema)
                logger.info(f"Successfully persisted {len(generated_alerts_schemas)} alerts for {provider}/{service} (Account: {account_id or 'N/A'}).")
            except Exception as e:
                logger.error(f"Failed to persist alerts for {provider}/{service} (Account: {account_id or 'N/A'}): {e}", exc_info=True)
                # Decidir se deve re-lançar a exceção ou apenas logar.
                # Por enquanto, apenas loga e retorna os alertas gerados (sem persistência).
            finally:
                db.close()

        logger.info(f"Analysis complete for {provider}/{service} (Account: {account_id or 'N/A'}). Found {len(generated_alerts_schemas)} potential alerts.")
        return generated_alerts_schemas

# Instância global do motor
policy_engine = PolicyEngine()

# Adicionar import de uuid no início do arquivo, se não estiver lá
import uuid
