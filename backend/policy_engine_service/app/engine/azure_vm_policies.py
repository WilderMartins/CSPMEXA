from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import AzureVirtualMachineDataInput, AzureNetworkInterfaceInput
from app.schemas.alert_schema import Alert
import uuid
import logging

logger = logging.getLogger(__name__)

class AzureVMPolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, vm: AzureVirtualMachineDataInput, account_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Definições de Políticas de VM do Azure ---

class AzureVMPublicIPPolicy(AzureVMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="AZURE_VM_PUBLIC_IP_DETECTED",
            title="Máquina Virtual Azure com Endereço IP Público",
            description="A Máquina Virtual Azure possui um ou mais endereços IP públicos associados diretamente a suas interfaces de rede, o que pode expô-la à internet.",
            severity="Medium",
            recommendation="Revise a necessidade de um IP público direto. Considere usar Load Balancers, Application Gateways ou Azure Bastion para acesso controlado. Se o IP público for necessário, garanta que Network Security Groups (NSGs) e firewalls de host estejam configurados para restringir o tráfego apenas às portas e origens necessárias."
        )

    def check(self, vm: AzureVirtualMachineDataInput, account_id: Optional[str]) -> Optional[Alert]:
        has_public_ip = False
        public_ip_details_list = []

        if vm.network_interfaces:
            for nic in vm.network_interfaces:
                if nic.ip_configurations:
                    for ip_config in nic.ip_configurations:
                        if ip_config.public_ip_address_details and ip_config.public_ip_address_details.ip_address:
                            has_public_ip = True
                            public_ip_details_list.append(
                                f"NIC: {nic.name or nic.id}, IP Público: {ip_config.public_ip_address_details.ip_address}"
                            )

        if has_public_ip:
            details = {
                "vm_name": vm.name,
                "vm_id": vm.id,
                "resource_group": vm.resource_group_name,
                "location": vm.location,
                "public_ips": public_ip_details_list
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=vm.id,
                resource_type="AzureVirtualMachine",
                account_id=account_id or "N/A", # subscription_id
                region=vm.location,
                provider="azure",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(public_ip_details_list)}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class AzureVMMissingNSGPolicy(AzureVMPolicy):
    def __init__(self):
        super().__init__(
            policy_id="AZURE_VM_MISSING_NSG",
            title="Máquina Virtual Azure (ou sua NIC) sem Network Security Group (NSG)",
            description="Uma ou mais interfaces de rede (NICs) associadas à Máquina Virtual Azure não possuem um Network Security Group (NSG) vinculado. NSGs são cruciais para filtrar o tráfego de rede de e para os recursos Azure.",
            severity="High",
            recommendation="Associe um Network Security Group (NSG) a cada interface de rede (NIC) da VM. Configure regras de entrada e saída no NSG para permitir apenas o tráfego estritamente necessário."
        )

    def check(self, vm: AzureVirtualMachineDataInput, account_id: Optional[str]) -> Optional[Alert]:
        nics_without_nsg: List[str] = []
        if vm.network_interfaces:
            for nic in vm.network_interfaces:
                if not nic.network_security_group or not nic.network_security_group.id:
                    nics_without_nsg.append(nic.name or nic.id)

        if nics_without_nsg:
            details = {
                "vm_name": vm.name,
                "vm_id": vm.id,
                "resource_group": vm.resource_group_name,
                "location": vm.location,
                "nics_missing_nsg": nics_without_nsg
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=vm.id,
                resource_type="AzureVirtualMachine",
                account_id=account_id or "N/A", # subscription_id
                region=vm.location,
                provider="azure",
                severity=self.severity,
                title=self.title,
                description=f"As seguintes NICs da VM '{vm.name}' não possuem NSG associado: {', '.join(nics_without_nsg)}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

# Adicionar mais políticas conforme o escopo definido:
# - AZURE_VM_DISK_UNENCRYPTED_AT_REST_PMK (requer dados de disco e criptografia no schema de input)
# - AZURE_VM_BOOT_LOGGING_DISABLED (requer dados de diagnóstico de boot no schema de input)

# Lista de todas as políticas de VM do Azure a serem avaliadas
azure_vm_policies_to_evaluate: List[AzureVMPolicy] = [
    AzureVMPublicIPPolicy(),
    AzureVMMissingNSGPolicy(),
]

def evaluate_azure_vm_policies(
    azure_vms_data: List[AzureVirtualMachineDataInput],
    subscription_id: Optional[str] # account_id para Azure é subscription_id
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(azure_vms_data)} VMs Azure para a subscrição {subscription_id or 'N/A'}.")

    for vm_data in azure_vms_data:
        if vm_data.error_details:
            logger.warning(f"Skipping Azure VM {vm_data.name} due to previous collection error: {vm_data.error_details}")
            # Poderíamos gerar um alerta informativo sobre o erro de coleta aqui se desejado.
            continue

        for policy in azure_vm_policies_to_evaluate:
            try:
                alert = policy.check(vm_data, subscription_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for Azure VM {vm_data.name}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    resource_id=vm_data.id,
                    resource_type="AzureVirtualMachine",
                    account_id=subscription_id or "N/A",
                    region=vm_data.location,
                    provider="azure",
                    severity="Medium",
                    title=f"Erro ao Avaliar Política de VM {policy.policy_id}",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para a VM Azure {vm_data.name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR_AZURE_VM",
                    details={"failed_policy_id": policy.policy_id, "vm_name": vm_data.name, "error": str(e)},
                    recommendation="Verifique os logs do Policy Engine para mais detalhes e a estrutura dos dados de entrada."
                ))

    logger.info(f"Avaliação de VMs Azure concluída para a subscrição {subscription_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts
