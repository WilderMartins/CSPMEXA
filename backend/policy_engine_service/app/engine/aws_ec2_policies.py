from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import EC2InstanceDataInput, EC2SecurityGroupDataInput, EC2IpPermission
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas EC2 ---

class EC2Policy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, resource: Any, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        """
        Verifica o recurso EC2 (Instância ou Security Group) contra esta política.
        Retorna um Alert se a política for violada, None caso contrário.
        """
        raise NotImplementedError

# --- Políticas para Security Groups ---

class EC2SGPublicIngressAllPortsPolicy(EC2Policy):
    def __init__(self):
        super().__init__(
            policy_id="EC2_SG_Public_Ingress_All_Ports",
            title="Security Group permite tráfego de entrada de qualquer IP para todas as portas",
            description="O Security Group possui uma regra de entrada que permite acesso de qualquer endereço IP (0.0.0.0/0 ou ::/0) a todas as portas (0-65535 ou protocolo 'any'/-1). Isso expõe todos os recursos associados a este SG a toda a internet em todas as portas.",
            severity="Critical",
            recommendation="Restrinja as regras de entrada para permitir acesso apenas dos IPs e portas estritamente necessários. Evite o uso de '0.0.0.0/0' ou '::/0' para todas as portas."
        )

    def check(self, sg: EC2SecurityGroupDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        is_public_all_ports = False
        offending_rule_details = []

        for perm in sg.ip_permissions: # sg.ip_permissions é List[EC2IpPermission]
            is_all_protocol = perm.ip_protocol == "-1" # "-1" significa todos os protocolos
            is_all_ports_tcp_udp = (perm.from_port == 0 and perm.to_port == 65535) or \
                                   (perm.from_port is None and perm.to_port is None and perm.ip_protocol in ["tcp", "udp"]) # Algumas APIs podem retornar assim

            is_any_port_for_protocol = is_all_protocol or is_all_ports_tcp_udp

            if is_any_port_for_protocol:
                for ip_range in perm.ip_ranges or []:
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        is_public_all_ports = True
                        offending_rule_details.append(f"Rule for IPv4 (0.0.0.0/0) on protocol '{perm.ip_protocol}' allows all ports.")
                        break
                if is_public_all_ports: break # Já encontrou uma regra crítica

                for ipv6_range in perm.ipv6_ranges or []:
                    if ipv6_range.get("CidrIpv6") == "::/0":
                        is_public_all_ports = True
                        offending_rule_details.append(f"Rule for IPv6 (::/0) on protocol '{perm.ip_protocol}' allows all ports.")
                        break
                if is_public_all_ports: break

        if is_public_all_ports:
            details = {
                "group_id": sg.group_id,
                "group_name": sg.group_name or "N/A",
                "vpc_id": sg.vpc_id or "N/A",
                "rules": offending_rule_details
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=sg.group_id,
                resource_type="EC2SecurityGroup",
                account_id=account_id or "N/A",
                region=region or "N/A",
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes da regra: {'; '.join(offending_rule_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class EC2SGPublicIngressSpecificPortPolicy(EC2Policy):
    def __init__(self, port: int, protocol: str, policy_id_suffix: str, title_suffix: str, severity: str = "High"):
        self.port = port
        self.protocol = protocol # e.g. "tcp", "udp"
        super().__init__(
            policy_id=f"EC2_SG_Public_Ingress_{policy_id_suffix.upper()}", # e.g., EC2_SG_Public_Ingress_SSH
            title=f"Security Group permite tráfego de entrada público para {title_suffix}", # e.g., SSH (porta 22)
            description=f"O Security Group possui uma regra de entrada que permite acesso de qualquer endereço IP (0.0.0.0/0 ou ::/0) para a porta {port}/{protocol}. Isso expõe o serviço {title_suffix} a toda a internet.",
            severity=severity,
            recommendation=f"Restrinja a regra de entrada para a porta {port}/{protocol} para permitir acesso apenas dos IPs estritamente necessários. Se o acesso público for necessário, considere limitar os IPs de origem ou usar um bastion host/VPN."
        )

    def check(self, sg: EC2SecurityGroupDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        is_public_specific_port = False
        offending_rule_details = []

        for perm in sg.ip_permissions:
            if perm.ip_protocol != self.protocol and self.protocol != "*": # Se self.protocol é "*", checa qualquer protocolo
                continue

            # Checa se a porta específica está dentro do range da permissão
            # (perm.from_port <= self.port <= perm.to_port)
            # Se from_port ou to_port for None, pode indicar 'todas as portas' para o protocolo, então precisa de cuidado.
            # Se from_port e to_port são None, e o protocolo casa, e o IP é público, é uma violação se self.port for "any".
            # Para uma porta específica, from_port e to_port devem incluir self.port.
            port_matches = False
            if perm.from_port is not None and perm.to_port is not None:
                if perm.from_port <= self.port <= perm.to_port:
                    port_matches = True
            elif perm.from_port is None and perm.to_port is None and perm.ip_protocol == self.protocol:
                # Se from/to são None, mas o protocolo específico (ex: tcp) casa, considera que a porta está inclusa.
                # Isso é uma interpretação comum para "todas as portas para este protocolo".
                port_matches = True


            if port_matches:
                for ip_range in perm.ip_ranges or []:
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        is_public_specific_port = True
                        offending_rule_details.append(f"Rule for IPv4 (0.0.0.0/0) allows access to port {self.port}/{self.protocol}.")
                        break
                if is_public_specific_port: break

                for ipv6_range in perm.ipv6_ranges or []:
                    if ipv6_range.get("CidrIpv6") == "::/0":
                        is_public_specific_port = True
                        offending_rule_details.append(f"Rule for IPv6 (::/0) allows access to port {self.port}/{self.protocol}.")
                        break
                if is_public_specific_port: break

        if is_public_specific_port:
            details = {
                "group_id": sg.group_id,
                "group_name": sg.group_name or "N/A",
                "vpc_id": sg.vpc_id or "N/A",
                "port": self.port,
                "protocol": self.protocol,
                "rules": offending_rule_details
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=sg.group_id,
                resource_type="EC2SecurityGroup",
                account_id=account_id or "N/A",
                region=region or "N/A",
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes da regra: {'; '.join(offending_rule_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Políticas para Instâncias EC2 ---

class EC2InstancePublicIPPolicy(EC2Policy):
    def __init__(self):
        super().__init__(
            policy_id="EC2_Instance_Public_IP",
            title="Instância EC2 possui um Endereço IP Público",
            description="A instância EC2 possui um endereço IP público associado, tornando-a potencialmente acessível pela internet.",
            severity="Informational", # Pode não ser uma violação por si só, mas é bom saber
            recommendation="Verifique se a instância necessita de um IP público. Se o acesso for apenas interno à VPC ou via VPN/DirectConnect, considere remover o IP público para reduzir a superfície de ataque. Utilize IPs Elásticos para IPs públicos estáticos, se necessário."
        )

    def check(self, instance: EC2InstanceDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        # O schema EC2InstanceDataInput já tem 'region'
        if instance.public_ip_address:
            details = {
                "instance_id": instance.instance_id,
                "public_ip": instance.public_ip_address,
                "private_ip": instance.private_ip_address or "N/A",
                "state": instance.state.name if instance.state else "N/A"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=instance.instance_id,
                resource_type="EC2Instance",
                account_id=account_id or "N/A",
                region=instance.region, # Usar a região da instância
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class EC2InstanceNoIAMProfilePolicy(EC2Policy):
    def __init__(self):
        super().__init__(
            policy_id="EC2_Instance_No_IAM_Profile",
            title="Instância EC2 sem Perfil IAM Associado",
            description="A instância EC2 não possui um perfil IAM (IAM Instance Profile) associado. Perfis IAM concedem permissões a aplicações rodando na instância para acessar outros serviços AWS de forma segura, sem a necessidade de armazenar credenciais na instância.",
            severity="Medium",
            recommendation="Associe um perfil IAM à instância EC2 com as permissões mínimas necessárias para suas aplicações. Evite usar credenciais de longo prazo diretamente nas instâncias."
        )

    def check(self, instance: EC2InstanceDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        if not instance.iam_instance_profile_arn:
            details = {
                "instance_id": instance.instance_id,
                "state": instance.state.name if instance.state else "N/A"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=instance.instance_id,
                resource_type="EC2Instance",
                account_id=account_id or "N/A",
                region=instance.region,
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Lista de Políticas EC2 ---
ec2_sg_policies_to_evaluate: List[EC2Policy] = [
    EC2SGPublicIngressAllPortsPolicy(),
    EC2SGPublicIngressSpecificPortPolicy(port=22, protocol="tcp", policy_id_suffix="SSH", title_suffix="SSH (porta 22)", severity="High"),
    EC2SGPublicIngressSpecificPortPolicy(port=3389, protocol="tcp", policy_id_suffix="RDP", title_suffix="RDP (porta 3389)", severity="High"),
    # Adicionar mais portas comuns aqui (ex: 80, 443, 3306, 5432, etc.)
    # Poderíamos ter uma lista de portas "perigosas" e iterar sobre elas para criar essas políticas dinamicamente.
]

ec2_instance_policies_to_evaluate: List[EC2Policy] = [
    EC2InstancePublicIPPolicy(),
    EC2InstanceNoIAMProfilePolicy(),
]

# Nova Política: Instância EC2 sem Tags Obrigatórias
REQUIRED_TAGS = ["Owner", "Environment", "CostCenter"] # Exemplo de tags obrigatórias, pode ser configurável
class EC2InstanceMissingRequiredTagsPolicy(EC2Policy):
    def __init__(self):
        super().__init__(
            policy_id="EC2_Instance_Missing_Required_Tags",
            title=f"Instância EC2 Não Possui Todas as Tags Obrigatórias ({', '.join(REQUIRED_TAGS)})",
            description=f"A instância EC2 não possui todas as tags obrigatórias configuradas: {', '.join(REQUIRED_TAGS)}. Tags são essenciais para gerenciamento de custos, responsabilidade e automação.",
            severity="Low", # Ou Medium, dependendo da importância das tags para a organização
            recommendation=f"Adicione as tags obrigatórias ({', '.join(REQUIRED_TAGS)}) à instância EC2 para melhor organização e governança."
        )

    def check(self, instance: EC2InstanceDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        instance_tags = {tag.get("Key"): tag.get("Value") for tag in instance.tags or []}
        missing_tags = [req_tag for req_tag in REQUIRED_TAGS if req_tag not in instance_tags]

        if missing_tags:
            details = {
                "instance_id": instance.instance_id,
                "current_tags": instance_tags,
                "required_tags": REQUIRED_TAGS,
                "missing_tags": missing_tags
            }
            return Alert(
                id=str(uuid.uuid4()), resource_id=instance.instance_id, resource_type="EC2Instance",
                account_id=account_id or "N/A", region=instance.region, provider="aws",
                severity=self.severity, title=self.title,
                description=f"A instância EC2 '{instance.instance_id}' não possui as seguintes tags obrigatórias: {', '.join(missing_tags)}.",
                policy_id=self.policy_id, details=details, recommendation=self.recommendation
            )
        return None
ec2_instance_policies_to_evaluate.append(EC2InstanceMissingRequiredTagsPolicy())


# Nova Política: Instância EC2 usando AMI não aprovada/desatualizada
# Esta política é mais complexa pois requer uma fonte de dados externa ou configuração
# sobre quais AMIs são aprovadas, desatualizadas ou vulneráveis.
# Para este exemplo, vamos simular com uma lista mockada.
DISAPPROVED_AMIS = ["ami-bad123", "ami-old456"] # Exemplo
class EC2InstanceUnapprovedAMIPolicy(EC2Policy):
    def __init__(self):
        super().__init__(
            policy_id="EC2_Instance_Using_Unapproved_AMI",
            title="Instância EC2 Utilizando AMI Não Aprovada ou Desatualizada",
            description="A instância EC2 está utilizando uma Amazon Machine Image (AMI) que não está na lista de AMIs aprovadas ou é conhecida por ser desatualizada/vulnerável.",
            severity="Medium", # Pode ser High se a AMI for conhecida por ter vulnerabilidades críticas
            recommendation="Substitua a instância por uma nova utilizando uma AMI aprovada e atualizada. Mantenha uma lista de AMIs padrão e seguras para uso na organização."
        )

    def check(self, instance: EC2InstanceDataInput, account_id: Optional[str], region: Optional[str]) -> Optional[Alert]:
        if instance.image_id and instance.image_id in DISAPPROVED_AMIS:
            details = {
                "instance_id": instance.instance_id,
                "image_id_used": instance.image_id,
                "list_of_disapproved_amis_checked": DISAPPROVED_AMIS # Para referência no alerta
            }
            return Alert(
                id=str(uuid.uuid4()), resource_id=instance.instance_id, resource_type="EC2Instance",
                account_id=account_id or "N/A", region=instance.region, provider="aws",
                severity=self.severity, title=self.title,
                description=f"A instância EC2 '{instance.instance_id}' está usando a AMI '{instance.image_id}', que não é aprovada ou é desatualizada.",
                policy_id=self.policy_id, details=details, recommendation=self.recommendation
            )
        return None
ec2_instance_policies_to_evaluate.append(EC2InstanceUnapprovedAMIPolicy())


# --- Funções de Avaliação ---

def evaluate_ec2_sg_policies(security_groups_data: List[EC2SecurityGroupDataInput], account_id: Optional[str], region: Optional[str]) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(security_groups_data)} Security Groups na região {region} para a conta {account_id or 'N/A'}.")

    for sg in security_groups_data:
        # sg.error_details não está no schema EC2SecurityGroupDataInput, mas poderia ser adicionado se o collector o provesse.
        # Assumindo que SGs com erro de coleta não chegam aqui ou são filtrados antes.

        for policy in ec2_sg_policies_to_evaluate:
            try:
                alert = policy.check(sg, account_id, region) # Passa a região do grupo de SGs
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for SG {sg.group_id} in region {region}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=sg.group_id, resource_type="EC2SecurityGroup",
                    account_id=account_id or "N/A", region=region or "N/A", provider="aws",
                    severity="Medium", title=f"Erro ao Avaliar Política {policy.policy_id} para SG",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para o SG {sg.group_id}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR", details={"failed_policy_id": policy.policy_id, "sg_id": sg.group_id},
                    recommendation="Verifique os logs do Policy Engine."
                ))
    return all_alerts

def evaluate_ec2_instance_policies(instances_data: List[EC2InstanceDataInput], account_id: Optional[str]) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(instances_data)} instâncias EC2 para a conta {account_id or 'N/A'}.")

    for instance in instances_data:
        if instance.error_details:
            logger.warning(f"Skipping instance {instance.instance_id} due to previous collection error: {instance.error_details}")
            continue

        # A região da instância está em instance.region
        instance_region = instance.region

        for policy in ec2_instance_policies_to_evaluate:
            try:
                # A política de instância pode usar instance.region diretamente.
                alert = policy.check(instance, account_id, instance_region)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for instance {instance.instance_id}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=instance.instance_id, resource_type="EC2Instance",
                    account_id=account_id or "N/A", region=instance_region, provider="aws",
                    severity="Medium", title=f"Erro ao Avaliar Política {policy.policy_id} para Instância",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para a instância {instance.instance_id}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR", details={"failed_policy_id": policy.policy_id, "instance_id": instance.instance_id},
                    recommendation="Verifique os logs do Policy Engine."
                ))
    return all_alerts
