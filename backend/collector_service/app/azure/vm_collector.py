from typing import List, Dict, Any, Optional
from azure.mgmt.compute.models import VirtualMachine
from azure.mgmt.network import NetworkManagementClient # Para buscar IPs e NSGs
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from .azure_client_manager import get_compute_management_client, get_azure_credentials
from app.schemas.azure.azure_compute import AzureVirtualMachineData, AzureNetworkInterface, AzureIPConfiguration, AzurePublicIPAddress, AzureNetworkSecurityGroupInfo
import logging

logger = logging.getLogger(__name__)

def get_network_management_client(subscription_id: str):
    """Helper para criar NetworkManagementClient."""
    credential = get_azure_credentials()
    return NetworkManagementClient(credential=credential, subscription_id=subscription_id)

async def get_azure_vm_data(subscription_id: str) -> List[AzureVirtualMachineData]:
    collected_vms: List[AzureVirtualMachineData] = []

    try:
        compute_client = get_compute_management_client(subscription_id)
        network_client = get_network_management_client(subscription_id) # Criado uma vez por subscrição

        vm_list = compute_client.virtual_machines.list_all()

        for vm_raw in vm_list:
            vm: VirtualMachine = vm_raw # Para type hinting
            vm_id = vm.id
            vm_name = vm.name
            location = vm.location
            vm_size = vm.hardware_profile.vm_size if vm.hardware_profile else None
            os_type = vm.storage_profile.os_disk.os_type.value if vm.storage_profile and vm.storage_profile.os_disk else None

            # Obter estado da VM (PowerState)
            # A instância de VM de list_all() pode não ter o estado detalhado.
            # É preciso chamar virtual_machines.instance_view(resource_group_name, vm_name)
            power_state = "Unknown"
            resource_group_name = _extract_resource_group_from_id(vm_id)
            if resource_group_name:
                try:
                    instance_view = compute_client.virtual_machines.instance_view(resource_group_name, vm_name)
                    for status in instance_view.statuses:
                        if status.code.startswith("PowerState/"):
                            power_state = status.display_status # e.g. "VM running", "VM deallocated"
                            break
                except Exception as e:
                    logger.warning(f"Could not get instance view for VM {vm_name} in RG {resource_group_name}: {e}")

            tags_dict: Optional[Dict[str, str]] = vm.tags

            network_interfaces_data: List[AzureNetworkInterface] = []
            if vm.network_profile and vm.network_profile.network_interfaces:
                for nic_ref in vm.network_profile.network_interfaces:
                    nic_id = nic_ref.id
                    nic_name = _extract_resource_name_from_id(nic_id)
                    nic_rg = _extract_resource_group_from_id(nic_id)

                    public_ip_addresses_nic: List[AzurePublicIPAddress] = []
                    ip_configurations_data: List[AzureIPConfiguration] = []
                    nsg_info: Optional[AzureNetworkSecurityGroupInfo] = None

                    if nic_rg and nic_name:
                        try:
                            nic_details = network_client.network_interfaces.get(nic_rg, nic_name)
                            if nic_details.network_security_group:
                                nsg_ref_id = nic_details.network_security_group.id
                                nsg_info = AzureNetworkSecurityGroupInfo(
                                    id=nsg_ref_id,
                                    name=_extract_resource_name_from_id(nsg_ref_id),
                                    resource_group=_extract_resource_group_from_id(nsg_ref_id)
                                )

                            if nic_details.ip_configurations:
                                for ip_config in nic_details.ip_configurations:
                                    public_ip_data = None
                                    if ip_config.public_ip_address:
                                        pip_id = ip_config.public_ip_address.id
                                        pip_name = _extract_resource_name_from_id(pip_id)
                                        pip_rg = _extract_resource_group_from_id(pip_id)
                                        pip_address = "N/A" # Precisa buscar o objeto PublicIPAddress
                                        if pip_rg and pip_name:
                                            try:
                                                pip_details = network_client.public_ip_addresses.get(pip_rg, pip_name)
                                                pip_address = pip_details.ip_address
                                            except Exception as e_pip:
                                                logger.warning(f"Could not get Public IP details for {pip_name}: {e_pip}")

                                        public_ip_data = AzurePublicIPAddress(
                                            id=pip_id,
                                            name=pip_name,
                                            ip_address=pip_address,
                                            resource_group=pip_rg
                                        )
                                        public_ip_addresses_nic.append(public_ip_data)

                                    ip_configurations_data.append(AzureIPConfiguration(
                                        name=ip_config.name,
                                        private_ip_address=ip_config.private_ip_address,
                                        public_ip_address_details=public_ip_data # Armazena o objeto detalhado
                                    ))
                        except Exception as e_nic:
                            logger.warning(f"Could not get details for NIC {nic_name} in RG {nic_rg}: {e_nic}")

                    network_interfaces_data.append(AzureNetworkInterface(
                        id=nic_id,
                        name=nic_name,
                        resource_group=nic_rg,
                        ip_configurations=ip_configurations_data,
                        network_security_group=nsg_info
                    ))

            vm_data = AzureVirtualMachineData(
                id=vm_id,
                name=vm_name,
                location=location,
                resource_group_name=resource_group_name,
                size=vm_size,
                os_type=os_type,
                power_state=power_state,
                tags=tags_dict,
                network_interfaces=network_interfaces_data,
                # Campos a serem preenchidos se necessário para políticas:
                # public_ip_addresses = [pip.ip_address for nic in network_interfaces_data for config in nic.ip_configurations if config.public_ip_address_details for pip in [config.public_ip_address_details] if pip.ip_address],
                # private_ip_addresses = [config.private_ip_address for nic in network_interfaces_data for config in nic.ip_configurations if config.private_ip_address],
            )
            collected_vms.append(vm_data)

    except Exception as e:
        logger.error(f"Error collecting Azure VM data for subscription {subscription_id}: {e}", exc_info=True)
        # Em um cenário real, poderíamos querer retornar uma lista parcial com um erro agregado,
        # ou levantar uma exceção para ser tratada pelo controller.
        # Por enquanto, retorna o que foi coletado antes do erro.
        # Ou, para ser mais robusto, adicionar um campo error_details a cada VM_data ou ao response global.
        # Para este MVP, vamos simplificar. Se houver um erro geral, a lista pode estar vazia ou parcial.
        # O ideal seria capturar exceções por VM e adicionar a `error_details` no `AzureVirtualMachineData`.
    return collected_vms

# Funções auxiliares para extrair nomes de IDs do Azure
def _extract_resource_group_from_id(resource_id: Optional[str]) -> Optional[str]:
    if not resource_id: return None
    try:
        return resource_id.split('/resourceGroups/')[1].split('/')[0]
    except IndexError:
        logger.warning(f"Could not parse resource group from ID: {resource_id}")
        return None

def _extract_resource_name_from_id(resource_id: Optional[str]) -> Optional[str]:
    if not resource_id: return None
    try:
        return resource_id.split('/')[-1]
    except IndexError:
        logger.warning(f"Could not parse resource name from ID: {resource_id}")
        return None

# Adicionar azure-mgmt-network aos requirements se ainda não estiver
# echo "azure-mgmt-network~=25.2.0" >> backend/collector_service/requirements.txt
# (Feito no passo de adicionar dependências, mas verificar a versão)
# A versão do azure-mgmt-network usada implicitamente pelo azure-mgmt-compute pode ser suficiente
# mas é bom ter explícito se usarmos diretamente como acima.
# O azure-mgmt-compute já depende de uma versão do azure-mgmt-network.
# No entanto, para usar `NetworkManagementClient` diretamente, é melhor adicioná-lo.
# Vou adicionar ao `requirements.txt` para garantir.
# (Já adicionei azure-mgmt-resource, que deve ser suficiente, mas vou adicionar network também para clareza)
# Correção: `azure-mgmt-resource` é para grupos de recursos. `azure-mgmt-network` é para NICs, IPs, NSGs.
# A dependência `azure-mgmt-network` é necessária.
```

E agora os schemas Pydantic correspondentes em `backend/collector_service/app/schemas/azure/azure_compute.py`:
