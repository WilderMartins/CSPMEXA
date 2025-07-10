from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import HuaweiECSServerDataInput, HuaweiVPCSecurityGroupInput, HuaweiVPCSecurityGroupRuleInput
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas Huawei ECS/VPC ---
class HuaweiComputePolicy: # Nome genérico para ECS e VPC SG
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, resource: Any, account_id: Optional[str], region_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Políticas para Huawei ECS Servers (VMs) ---

class HuaweiECSPublicIPPolicy(HuaweiComputePolicy):
    def __init__(self):
        super().__init__(
            policy_id="HUAWEI_ECS_Instance_Public_IP",
            title="Instância ECS (VM) com Endereço IP Público",
            description="A instância ECS possui um ou mais endereços IP públicos (EIP ou outros) associados, tornando-a potencialmente acessível pela internet.",
            severity="Informational",
            recommendation="Verifique se a instância necessita de um IP público. Para acesso interno, use IPs privados. Se o acesso público for necessário, restrinja o acesso usando Security Groups."
        )

    def check(self, instance: HuaweiECSServerDataInput, account_id: Optional[str], region_id: Optional[str]) -> Optional[Alert]:
        if instance.public_ips and len(instance.public_ips) > 0:
            details = {
                "server_id": instance.id,
                "server_name": instance.name,
                "account_id": account_id or instance.project_id or "N/A",
                "region": region_id or instance.region_id or "N/A",
                "public_ips": instance.public_ips,
                "private_ips": instance.private_ips
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=instance.id,
                resource_type="HuaweiECSServer",
                account_id=details["account_id"],
                region=details["region"],
                provider="huawei",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} IPs públicos encontrados: {', '.join(instance.public_ips)}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# Adicionar política para verificar se ECS usa key pair, se não usar senha (mais complexo)
# Adicionar política para verificar se ECS está associado a SGs muito permissivos (requer dados de SG)

# --- Políticas para Huawei VPC Security Groups ---

class HuaweiVPCSGAllowsPublicIngressToPortPolicy(HuaweiComputePolicy):
    def __init__(self, port: int, protocol: str, policy_id_suffix: str, title_suffix: str, severity: str = "High"):
        self.port = port
        self.protocol = protocol.lower() # tcp, udp, icmp. "any" para qualquer protocolo.
        super().__init__(
            policy_id=f"HUAWEI_VPC_SG_Public_Ingress_{policy_id_suffix.upper()}",
            title=f"Security Group VPC permite tráfego de entrada público para {title_suffix}",
            description=f"O Security Group VPC possui uma regra de entrada que permite acesso de qualquer endereço IP (0.0.0.0/0) para a porta {port}/{protocol}.",
            severity=severity,
            recommendation=f"Restrinja a regra de entrada para a porta {port}/{protocol} para permitir acesso apenas dos IPs de origem estritamente necessários."
        )

    def check(self, sg: HuaweiVPCSecurityGroupInput, account_id: Optional[str], region_id: Optional[str]) -> Optional[Alert]:
        is_public_specific_port = False
        offending_rule_details_list = []

        for rule in sg.security_group_rules:
            if rule.direction != "ingress":
                continue

            protocol_matches = False
            if self.protocol == "any" or not rule.protocol: # Se a regra não especifica protocolo, é 'any'
                protocol_matches = True
            elif rule.protocol and self.protocol == rule.protocol.lower():
                protocol_matches = True

            port_matches = False
            if protocol_matches:
                if not rule.port_range_min and not rule.port_range_max: # Todas as portas para o protocolo
                    port_matches = True
                elif rule.port_range_min is not None and rule.port_range_max is not None:
                    if rule.port_range_min <= self.port <= rule.port_range_max:
                        port_matches = True
                elif rule.port_range_min == self.port and rule.port_range_max is None: # Porta única
                     port_matches = True
                elif rule.port_range_min is None and rule.port_range_max == self.port: # Porta única
                     port_matches = True


            if port_matches and rule.remote_ip_prefix == "0.0.0.0/0": # Checa apenas IPv4 por simplicidade no MVP
                is_public_specific_port = True
                offending_rule_details_list.append(
                    f"Rule ID '{rule.id}': Protocol '{rule.protocol or 'any'}', Ports '{rule.port_range_min or 'any'}-{rule.port_range_max or 'any'}' from '0.0.0.0/0'."
                )

        if is_public_specific_port:
            details = {
                "sg_id": sg.id,
                "sg_name": sg.name,
                "account_id": account_id or sg.project_id_from_collector or "N/A",
                "region": region_id or sg.region_id or "N/A",
                "port": self.port,
                "protocol": self.protocol,
                "offending_rules": offending_rule_details_list
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=sg.id,
                resource_type="HuaweiVPCSecurityGroup",
                account_id=details["account_id"],
                region=details["region"],
                provider="huawei",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(offending_rule_details_list)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None


# --- Listas de Políticas ---
huawei_ecs_instance_policies_to_evaluate: List[HuaweiComputePolicy] = [
    HuaweiECSPublicIPPolicy(),
]

huawei_vpc_sg_policies_to_evaluate: List[HuaweiComputePolicy] = [
    HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH (porta 22)", severity="Critical"),
    HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=3389, protocol="tcp", policy_id_suffix="RDP", title_suffix="RDP (porta 3389)", severity="Critical"),
    HuaweiVPCSGAllowsPublicIngressToPortPolicy(port=0, protocol="any", policy_id_suffix="ANY_ALL", title_suffix="Qualquer Porta/Protocolo", severity="Critical"), # Representa todas as portas/protocolos
]

# --- Funções de Avaliação ---
def evaluate_huawei_ecs_instance_policies(
    instances_data: List[HuaweiECSServerDataInput],
    account_id: Optional[str], # project_id ou domain_id
    region_id: Optional[str]
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(instances_data)} instâncias Huawei ECS para conta {account_id or 'N/A'} na região {region_id or 'N/A'}.")
    for instance in instances_data:
        if instance.error_details:
            logger.warning(f"Skipping Huawei ECS {instance.name} due to collection error: {instance.error_details}")
            continue
        for policy_def in huawei_ecs_instance_policies_to_evaluate:
            try:
                alert = policy_def.check(instance, account_id, region_id) # Passar region_id também
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_def.policy_id} for Huawei ECS {instance.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine
    return all_alerts

def evaluate_huawei_vpc_sg_policies(
    sgs_data: List[HuaweiVPCSecurityGroupInput],
    account_id: Optional[str], # project_id ou domain_id
    region_id: Optional[str]
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(sgs_data)} Huawei VPC SGs para conta {account_id or 'N/A'} na região {region_id or 'N/A'}.")
    for sg in sgs_data:
        if sg.error_details:
            logger.warning(f"Skipping Huawei VPC SG {sg.name} due to collection error: {sg.error_details}")
            continue
        for policy_def in huawei_vpc_sg_policies_to_evaluate:
            try:
                alert = policy_def.check(sg, account_id, region_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_def.policy_id} for Huawei VPC SG {sg.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine
    return all_alerts
