from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import AnalysisRequest, S3BucketDataInput, EC2InstanceDataInput, EC2SecurityGroupDataInput, IAMUserDataInput
from app.schemas.alert_schema import Alert
from app.engine import aws_s3_policies, aws_ec2_policies, aws_iam_policies
import logging

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self):
        # No futuro, poderíamos carregar configurações de políticas, pesos, etc.
        pass

    def analyze(self, request_data: AnalysisRequest) -> List[Alert]:
        """
        Ponto de entrada principal para analisar os dados de recursos da nuvem.
        Direciona os dados para os módulos de avaliação de políticas apropriados.
        """
        alerts: List[Alert] = []

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
                # Validar se 'data' é List[S3BucketDataInput]
                # Pydantic já deve ter feito isso se o tipo em AnalysisRequest.data for específico
                # Se AnalysisRequest.data é List[Dict], precisamos converter/validar aqui.
                # Assumindo que o controller já fez o parse para o tipo correto com base no 'service'.
                s3_alerts = aws_s3_policies.evaluate_s3_policies(
                    s3_buckets_data=data, # type: ignore # Data já deve ser List[S3BucketDataInput]
                    account_id=account_id
                )
                alerts.extend(s3_alerts)

            elif service == "ec2_instances":
                # O schema EC2InstanceDataInput já inclui a região por instância.
                ec2_instance_alerts = aws_ec2_policies.evaluate_ec2_instance_policies(
                    instances_data=data, # type: ignore
                    account_id=account_id
                )
                alerts.extend(ec2_instance_alerts)

            elif service == "ec2_security_groups":
                # EC2SecurityGroupDataInput agora tem 'region', então podemos agrupar.
                if not all(isinstance(item, EC2SecurityGroupDataInput) for item in data):
                     logger.error("Data for ec2_security_groups is not of type List[EC2SecurityGroupDataInput]. Skipping.")
                else:
                    sgs_by_region_map: Dict[str, List[EC2SecurityGroupDataInput]] = {}
                    for sg_input in data: # data é List[EC2SecurityGroupDataInput]
                        # O schema EC2SecurityGroupDataInput agora deve ter 'region'.
                        # Se sg_input.region for None ou não existir (devido a um erro de parse anterior ou dado antigo),
                        # ainda podemos precisar de um fallback, mas o ideal é que seja sempre presente.
                        sg_region = sg_input.region if hasattr(sg_input, 'region') and sg_input.region else 'unknown_region_sg'
                        if sg_region not in sgs_by_region_map:
                            sgs_by_region_map[sg_region] = []
                        sgs_by_region_map[sg_region].append(sg_input)

                    for reg, sgs_list in sgs_by_region_map.items():
                        if reg == 'unknown_region_sg':
                            logger.warning("Processing EC2 Security Groups with an undetermined region. Region-specific context for alerts might be impacted.")

                        sg_alerts = aws_ec2_policies.evaluate_ec2_sg_policies(
                            security_groups_data=sgs_list, # Passa a lista de SGs para esta região
                            account_id=account_id,
                            region=reg # Passa a chave da região
                        )
                        alerts.extend(sg_alerts)

            elif service == "iam_users":
                iam_user_alerts = aws_iam_policies.evaluate_iam_user_policies(
                    users_data=data, # type: ignore
                    account_id=account_id
                )
                alerts.extend(iam_user_alerts)

            elif service == "iam_roles":
                # Supondo que IAMRoleDataInput está definido em input_data_schema e que aws_iam_policies
                # tem uma função evaluate_iam_role_policies.
                # Se não, precisaremos adicionar/ajustar.
                if not all(isinstance(item, IAMRoleDataInput if 'IAMRoleDataInput' in globals() else dict) for item in data): # type: ignore
                     logger.error(f"Data for iam_roles is not of expected type. Skipping. Data type: {type(data[0]) if data else 'empty'}")
                else:
                    # Placeholder: chamar a função de avaliação de roles quando implementada
                    # from app.schemas.input_data_schema import IAMRoleDataInput # Certifique-se que está importado
                    # role_alerts = aws_iam_policies.evaluate_iam_role_policies(
                    #     roles_data=data, # type: ignore
                    #     account_id=account_id
                    # )
                    # alerts.extend(role_alerts)
                    logger.info("IAM role policy evaluation not yet fully implemented in core_engine.")
                    pass # Remover pass quando a avaliação de roles estiver pronta

            elif service == "iam_policies": # Para políticas gerenciadas
                # Supondo que IAMPolicyDataInput está definido e aws_iam_policies
                # tem uma função evaluate_iam_managed_policy_policies.
                if not all(isinstance(item, IAMPolicyDataInput if 'IAMPolicyDataInput' in globals() else dict) for item in data): # type: ignore
                    logger.error(f"Data for iam_policies is not of expected type. Skipping. Data type: {type(data[0]) if data else 'empty'}")
                else:
                    # Placeholder:
                    # from app.schemas.input_data_schema import IAMPolicyDataInput # Certifique-se que está importado
                    # policy_alerts = aws_iam_policies.evaluate_iam_managed_policy_policies(
                    #    policies_data=data, # type: ignore
                    #    account_id=account_id
                    # )
                    # alerts.extend(policy_alerts)
                    logger.info("IAM managed policy evaluation not yet fully implemented in core_engine.")
                    pass # Remover pass quando a avaliação de políticas gerenciadas estiver pronta
            else:
                logger.warning(f"Unsupported AWS service for analysis: {service}")
        else:
            logger.warning(f"Unsupported provider for analysis: {provider}")

        logger.info(f"Analysis complete for {provider}/{service}. Found {len(alerts)} potential alerts.")
        return alerts

# Instância global do motor (pode ser gerenciada por dependência FastAPI se necessário)
policy_engine = PolicyEngine()
