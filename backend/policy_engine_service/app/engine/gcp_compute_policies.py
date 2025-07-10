from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import GCPComputeInstanceDataInput, GCPFirewallDataInput, GCPFirewallAllowedRuleInput # Alterado para Input
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas GCP Compute ---
class GCPComputePolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, resource: Any, project_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Políticas para GCP Compute Instances ---

class GCPComputeInstancePublicIPPolicy(GCPComputePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Compute_Instance_Public_IP",
            title="Instância de VM do Compute Engine com Endereço IP Público",
            description="A instância de VM possui um ou mais endereços IP públicos associados, tornando-a potencialmente acessível pela internet.",
            severity="Informational",
            recommendation="Verifique se a instância necessita de um IP público. Se o acesso for apenas interno à VPC ou via VPN/bastion, considere remover os IPs públicos para reduzir a superfície de ataque."
        )

    def check(self, instance: GCPComputeInstanceDataInput, project_id: Optional[str]) -> Optional[Alert]:
        if instance.public_ip_addresses and len(instance.public_ip_addresses) > 0:
            details = {
                "instance_name": instance.name,
                "instance_id": instance.id,
                "project_id": project_id or instance.project_id or "N/A",
                "zone": instance.extracted_zone,
                "public_ips": instance.public_ip_addresses,
                "private_ips": instance.private_ip_addresses
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=instance.id,
                resource_type="GCPComputeInstance",
                account_id=project_id or instance.project_id or "N/A",
                region=instance.extracted_zone, # Zona é mais específica que região para instâncias
                provider="gcp",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} IPs públicos encontrados: {', '.join(instance.public_ip_addresses)}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

class GCPComputeInstanceDefaultServiceAccountFullAccessPolicy(GCPComputePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Compute_Instance_Default_SA_Full_Access",
            title="Instância de VM usando Service Account Padrão com Acesso Total às APIs",
            description="A instância de VM está configurada para usar a service account padrão do Compute Engine com o escopo de acesso 'cloud-platform' (acesso total a todas as APIs do Google Cloud). Isso concede permissões excessivas à instância.",
            severity="High",
            recommendation="Evite usar a service account padrão com escopo de acesso total. Crie service accounts dedicadas com permissões mínimas necessárias para cada aplicação/instância ou use escopos de acesso mais restritos."
        )

    def check(self, instance: GCPComputeInstanceDataInput, project_id: Optional[str]) -> Optional[Alert]:
        if instance.service_accounts:
            for sa in instance.service_accounts:
                # Service account padrão do Compute: {PROJECT_NUMBER}-compute@developer.gserviceaccount.com
                # Ou simplesmente "default" se o email não for totalmente qualificado no dado.
                is_default_sa_email = sa.email and ("-compute@developer.gserviceaccount.com" in sa.email or sa.email == "default")

                has_full_access_scope = False
                if sa.scopes:
                    full_access_scopes = [
                        "https://www.googleapis.com/auth/cloud-platform"
                        # "cloud-platform" # Alias curto
                    ]
                    if any(scope_url in full_access_scopes for scope_url in sa.scopes):
                        has_full_access_scope = True

                if is_default_sa_email and has_full_access_scope:
                    details = {
                        "instance_name": instance.name,
                        "instance_id": instance.id,
                        "project_id": project_id or instance.project_id or "N/A",
                        "zone": instance.extracted_zone,
                        "service_account_email": sa.email,
                        "scopes": sa.scopes
                    }
                    return Alert(
                        id=str(uuid.uuid4()),
                        resource_id=instance.id,
                        resource_type="GCPComputeInstance",
                        account_id=project_id or instance.project_id or "N/A",
                        region=instance.extracted_zone,
                        provider="gcp",
                        severity=self.severity,
                        title=self.title,
                        description=f"{self.description} Service Account: {sa.email}.",
                        policy_id=self.policy_id,
                        details=details,
                        recommendation=self.recommendation
                    )
        return None


# --- Políticas para GCP Firewalls VPC ---
class GCPFirewallPublicIngressAnyPortPolicy(GCPComputePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Firewall_Public_Ingress_Any_Port",
            title="Firewall VPC permite tráfego de entrada de qualquer IP para qualquer protocolo/porta",
            description="A regra de firewall permite tráfego de entrada de qualquer origem (0.0.0.0/0) para todos os protocolos e portas em instâncias com a tag de destino ou service account associada.",
            severity="Critical",
            recommendation="Restrinja as regras de firewall para permitir tráfego apenas de IPs e para portas/protocolos estritamente necessários. Evite '0.0.0.0/0' com 'all' ou protocolos muito amplos."
        )

    def check(self, firewall: GCPFirewallDataInput, project_id: Optional[str]) -> Optional[Alert]:
        if firewall.direction != "INGRESS" or firewall.disabled:
            return None

        is_public_any_port = False
        offending_rule_details = []

        if "0.0.0.0/0" in (firewall.source_ranges or []):
            if firewall.allowed:
                for rule in firewall.allowed:
                    # "all" é um valor comum para ipProtocol em firewalls GCP para todos os protocolos
                    if rule.ip_protocol.lower() == "all" or not rule.ports: # Se ports for None/vazio, significa todas as portas para o protocolo
                        is_public_any_port = True
                        offending_rule_details.append(f"Allowed rule for protocol '{rule.ip_protocol}' (all ports) from 0.0.0.0/0.")
                        break
            elif not firewall.allowed and not firewall.denied: # Se não há allowed/denied, default é deny, mas a regra em si pode ser para 'all'
                 pass # Não é uma regra "allow all" explícita.

        if is_public_any_port:
            details = {
                "firewall_name": firewall.name,
                "firewall_id": firewall.id,
                "project_id": project_id or firewall.project_id or "N/A",
                "network": firewall.extracted_network_name,
                "source_ranges": firewall.source_ranges,
                "allowed_rules": [r.model_dump(exclude_none=True) for r in firewall.allowed] if firewall.allowed else []
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=firewall.id,
                resource_type="GCPFirewallRule",
                account_id=project_id or firewall.project_id or "N/A",
                region="global", # Firewalls VPC são globais, mas aplicadas a redes que podem ser regionais/globais
                provider="gcp",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(offending_rule_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation
            )
        return None

# --- Listas de Políticas ---
gcp_compute_instance_policies_to_evaluate: List[GCPComputePolicy] = [
    GCPComputeInstancePublicIPPolicy(),
    GCPComputeInstanceDefaultServiceAccountFullAccessPolicy(),
]

gcp_firewall_policies_to_evaluate: List[GCPComputePolicy] = [
    GCPFirewallPublicIngressAnyPortPolicy(),
    # Adicionar política para portas específicas (SSH, RDP) similar ao AWS
]

# --- Funções de Avaliação ---
def evaluate_gcp_compute_instance_policies(
    instances_data: List[GCPComputeInstanceDataInput],
    project_id: Optional[str]
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(instances_data)} Instâncias VM GCP para o projeto {project_id or 'N/A'}.")
    for instance in instances_data:
        if instance.error_details:
            logger.warning(f"Skipping GCP VM Instance {instance.name} due to collection error: {instance.error_details}")
            continue
        for policy in gcp_compute_instance_policies_to_evaluate:
            try:
                alert = policy.check(instance, project_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for GCP VM {instance.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine
    return all_alerts

def evaluate_gcp_firewall_policies(
    firewalls_data: List[GCPFirewallDataInput],
    project_id: Optional[str]
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(firewalls_data)} Firewalls GCP para o projeto {project_id or 'N/A'}.")
    for firewall in firewalls_data:
        if firewall.error_details:
            logger.warning(f"Skipping GCP Firewall {firewall.name} due to collection error: {firewall.error_details}")
            continue
        for policy in gcp_firewall_policies_to_evaluate:
            try:
                alert = policy.check(firewall, project_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for GCP Firewall {firewall.name}: {e}", exc_info=True)
                # Criar alerta de erro de engine
    return all_alerts
