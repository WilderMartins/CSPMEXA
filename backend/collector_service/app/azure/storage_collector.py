from typing import List, Optional
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.models import StorageAccount
from .azure_client_manager import get_storage_management_client
from app.schemas.azure.azure_storage import (
    AzureStorageAccountData,
    AzureStorageAccountSku,
    AzureStorageAccountNetworkRuleSet,
    AzureStorageAccountBlobProperties
)
import logging

logger = logging.getLogger(__name__)

# Funções auxiliares (se necessárias, como _extract_resource_group_from_id, podem ser importadas ou duplicadas)
def _extract_resource_group_from_id(resource_id: Optional[str]) -> Optional[str]:
    if not resource_id: return None
    try:
        return resource_id.split('/resourceGroups/')[1].split('/')[0]
    except IndexError:
        logger.warning(f"Could not parse resource group from ID: {resource_id}")
        return None

async def get_azure_storage_account_data(subscription_id: str) -> List[AzureStorageAccountData]:
    collected_accounts: List[AzureStorageAccountData] = []

    try:
        storage_client: StorageManagementClient = get_storage_management_client(subscription_id)
        account_list = storage_client.storage_accounts.list()

        for acc_raw in account_list:
            acc: StorageAccount = acc_raw # For type hinting
            account_id = acc.id
            account_name = acc.name
            location = acc.location
            resource_group = _extract_resource_group_from_id(account_id)
            error_msg = None

            blob_properties_data = None
            try:
                if resource_group and account_name:
                    # Obter propriedades do serviço Blob (para versionamento, logging etc.)
                    # O SDK pode ter mudado como isso é acessado.
                    # Anteriormente: storage_client.blob_services.get_service_properties(...)
                    # Agora, pode estar em storage_account.blob_properties ou via uma chamada separada.
                    # Para StorageManagementClient (azure-mgmt-storage), Blob service properties
                    # são geralmente obtidas com `blob_services.get_service_properties`.
                    blob_service_props = storage_client.blob_services.get_service_properties(
                        resource_group_name=resource_group,
                        account_name=account_name
                    )
                    blob_properties_data = AzureStorageAccountBlobProperties(
                        deleteRetentionPolicy_enabled=blob_service_props.delete_retention_policy.enabled if blob_service_props.delete_retention_policy else None,
                        containerDeleteRetentionPolicy_enabled=blob_service_props.container_delete_retention_policy.enabled if hasattr(blob_service_props, 'container_delete_retention_policy') and blob_service_props.container_delete_retention_policy else None,
                        isVersioningEnabled=blob_service_props.is_versioning_enabled if hasattr(blob_service_props, 'is_versioning_enabled') else None,
                        # Adicionar outros campos conforme necessário, ex: change_feed, restore_policy
                    )
            except Exception as e_blob_props:
                logger.warning(f"Could not get blob service properties for account {account_name} in RG {resource_group}: {e_blob_props}")
                error_msg = f"Blob service properties fetch failed: {str(e_blob_props)}; "


            # Network Rule Set (ACLs)
            network_rule_set_data = None
            if acc.network_rule_set:
                network_rule_set_data = AzureStorageAccountNetworkRuleSet(
                    defaultAction=acc.network_rule_set.default_action.value # Enum to string
                    # ip_rules, virtual_network_rules podem ser adicionados se necessário
                )

            account_data = AzureStorageAccountData(
                id=account_id,
                name=account_name,
                location=location,
                resource_group_name=resource_group,
                kind=acc.kind.value if acc.kind else None, # Enum to string
                sku=AzureStorageAccountSku(name=acc.sku.name.value, tier=acc.sku.tier.value if acc.sku.tier else None) if acc.sku else None, # Enums to string

                allow_blob_public_access=acc.allow_blob_public_access,
                minimum_tls_version=acc.minimum_tls_version.value if acc.minimum_tls_version else None, # Enum to string
                supports_https_traffic_only=acc.enable_https_traffic_only, # Nome da propriedade no SDK é enable_https_traffic_only

                network_rule_set=network_rule_set_data,
                blob_properties=blob_properties_data,

                tags=acc.tags,
                error_details=error_msg.strip() if error_msg else None
            )
            collected_accounts.append(account_data)

    except Exception as e:
        logger.error(f"Error collecting Azure Storage Account data for subscription {subscription_id}: {e}", exc_info=True)
        # Se um erro geral ocorrer (ex: credenciais), podemos querer levantar uma exceção
        # para ser tratada no controller e retornar um erro HTTP apropriado.
        # Para este exemplo, se houver um erro, a lista pode estar vazia ou parcial.
        # O ideal seria adicionar um erro global ao response se a coleta falhar completamente.
        # Se o erro for por conta, o `error_details` no `AzureStorageAccountData` seria usado.

    return collected_accounts

# Adicionar azure-mgmt-storage aos requirements se ainda não estiver.
# echo "azure-mgmt-storage~=21.0.0" >> backend/collector_service/requirements.txt
# (Verificar a versão mais recente ou compatível)
# A versão já está lá, mas é bom confirmar.
# O SDK do Azure é modular. `azure-identity` é para autenticação.
# `azure-mgmt-compute` para VMs. `azure-mgmt-storage` para Storage Accounts.
# `azure-mgmt-network` para NICs, IPs, NSGs, etc.
# `azure-mgmt-resource` para Resource Groups.
# Todas essas dependências devem estar no requirements.txt do collector-service.
# A versão do azure-mgmt-storage é 21.0.0 no requirements.txt, que está ok.
# A versão do azure-mgmt-compute é 30.0.0 no requirements.txt, ok.
# A versão do azure-mgmt-network é 25.2.0 no requirements.txt, ok.
# A versão do azure-mgmt-resource é 23.0.1 no requirements.txt, ok.
# A versão do azure-identity é 1.15.0 no requirements.txt, ok.

# Nota sobre `enable_https_traffic_only` vs `supports_https_traffic_only`:
# No SDK `azure-mgmt-storage`, o modelo `StorageAccountProperties` ou `StorageAccount`
# geralmente tem `enable_https_traffic_only` (um booleano).
# O schema Pydantic `AzureStorageAccountData` tem `supports_https_traffic_only`.
# Mapeei `acc.enable_https_traffic_only` para `supports_https_traffic_only` no schema.
# Isso está correto.

# Nota sobre Enums:
# Muitos campos no SDK do Azure são Enums (ex: acc.kind, acc.sku.name, acc.minimum_tls_version).
# É preciso converter para string usando `.value` ao popular os schemas Pydantic,
# se os schemas esperam strings. Ex: `kind=acc.kind.value`.
# Os schemas foram definidos com `Optional[str]`, então `.value` é apropriado.
# Para `network_rule_set.default_action`, o schema espera `str`, e `acc.network_rule_set.default_action` é um Enum (`DefaultAction`), então `.value` é necessário.
# Para `sku.name` e `sku.tier`, também são Enums (`SkuName`, `SkuTier`).
# Para `minimum_tls_version`, também é um Enum (`MinimumTlsVersion`).
# As conversões `.value` foram adicionadas.
