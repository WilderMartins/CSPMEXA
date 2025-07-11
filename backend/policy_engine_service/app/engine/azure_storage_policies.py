from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import AzureStorageAccountDataInput
from app.schemas.alert_schema import Alert
import uuid
import logging

logger = logging.getLogger(__name__)

class AzureStoragePolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, storage_account: AzureStorageAccountDataInput, account_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Definições de Políticas de Storage Accounts do Azure ---

class AzureStoragePublicAccessEnabledPolicy(AzureStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="AZURE_STORAGE_ACCOUNT_PUBLIC_ACCESS_ENABLED",
            title="Azure Storage Account permite acesso público a blobs",
            description="A configuração 'allowBlobPublicAccess' está habilitada para a Storage Account, permitindo potencialmente o acesso público anônimo a todos os blobs ou contêineres se não for restringido de outra forma.",
            severity="Critical",
            recommendation="Desabilite 'allowBlobPublicAccess' a nível de conta se o acesso público não for necessário. Gerencie o acesso público em nível de contêiner individual com cautela. Use identidades gerenciadas e RBAC do Azure para acesso seguro."
        )

    def check(self, storage_account: AzureStorageAccountDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if storage_account.allow_blob_public_access is True: # Explicitamente True
            details = {
                "storage_account_name": storage_account.name,
                "storage_account_id": storage_account.id,
                "resource_group": storage_account.resource_group_name,
                "location": storage_account.location,
                "allow_blob_public_access": True
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=storage_account.id,
                resource_type="AzureStorageAccount",
                account_id=account_id or "N/A", # subscription_id
                region=storage_account.location,
                provider="azure",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class AzureStorageHttpsTransferDisabledPolicy(AzureStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="AZURE_STORAGE_ACCOUNT_HTTPS_TRANSFER_DISABLED",
            title="Transferência segura (HTTPS) não exigida para Azure Storage Account",
            description="A Storage Account não está configurada para exigir tráfego HTTPS ('supportsHttpsTrafficOnly' é false). Isso permite conexões HTTP, que são inseguras.",
            severity="High",
            recommendation="Habilite a configuração 'Exigir transferência segura' (supportsHttpsTrafficOnly = true) nas configurações da Storage Account para garantir que todas as conexões sejam criptografadas via HTTPS."
        )

    def check(self, storage_account: AzureStorageAccountDataInput, account_id: Optional[str]) -> Optional[Alert]:
        # O schema de input tem supports_https_traffic_only
        if storage_account.supports_https_traffic_only is False: # Explicitamente False
            details = {
                "storage_account_name": storage_account.name,
                "storage_account_id": storage_account.id,
                "resource_group": storage_account.resource_group_name,
                "location": storage_account.location,
                "supports_https_traffic_only": False
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=storage_account.id,
                resource_type="AzureStorageAccount",
                account_id=account_id or "N/A", # subscription_id
                region=storage_account.location,
                provider="azure",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class AzureStorageBlobVersioningDisabledPolicy(AzureStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="AZURE_STORAGE_ACCOUNT_BLOB_VERSIONING_DISABLED",
            title="Versionamento de Blob desabilitado para Azure Storage Account",
            description="O versionamento de blob não está habilitado para o serviço de Blob da Storage Account. O versionamento protege contra exclusões ou modificações acidentais de blobs.",
            severity="Medium",
            recommendation="Habilite o versionamento de blob nas propriedades do serviço de Blob da Storage Account para proteger os dados e permitir a recuperação de versões anteriores."
        )

    def check(self, storage_account: AzureStorageAccountDataInput, account_id: Optional[str]) -> Optional[Alert]:
        versioning_enabled = False
        if storage_account.blob_properties and storage_account.blob_properties.is_versioning_enabled is True:
            versioning_enabled = True

        if not versioning_enabled:
            details = {
                "storage_account_name": storage_account.name,
                "storage_account_id": storage_account.id,
                "resource_group": storage_account.resource_group_name,
                "location": storage_account.location,
                "blob_versioning_status": "Disabled or Unknown"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=storage_account.id,
                resource_type="AzureStorageAccount",
                account_id=account_id or "N/A", # subscription_id
                region=storage_account.location,
                provider="azure",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

# AZURE_STORAGE_ACCOUNT_BLOB_LOGGING_DISABLED
# Esta política requer que a coleta de dados de diagnóstico/logging seja implementada
# no storage_collector.py e adicionada ao schema AzureStorageAccountBlobPropertiesInput.
# Por enquanto, esta política será um placeholder ou omitida até que os dados estejam disponíveis.
# Se `blob_properties` incluir informações de logging, ela pode ser implementada.
# Exemplo: `blob_properties.logging_analytics_enabled` (nome hipotético)

# Lista de todas as políticas de Storage Account do Azure a serem avaliadas
azure_storage_policies_to_evaluate: List[AzureStoragePolicy] = [
    AzureStoragePublicAccessEnabledPolicy(),
    AzureStorageHttpsTransferDisabledPolicy(),
    AzureStorageBlobVersioningDisabledPolicy(),
    # Adicionar política de logging aqui quando os dados estiverem disponíveis.
]

def evaluate_azure_storage_policies(
    azure_storage_accounts_data: List[AzureStorageAccountDataInput],
    subscription_id: Optional[str] # account_id para Azure é subscription_id
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(azure_storage_accounts_data)} Azure Storage Accounts para a subscrição {subscription_id or 'N/A'}.")

    for acc_data in azure_storage_accounts_data:
        if acc_data.error_details:
            logger.warning(f"Skipping Azure Storage Account {acc_data.name} due to previous collection error: {acc_data.error_details}")
            continue

        for policy in azure_storage_policies_to_evaluate:
            try:
                alert = policy.check(acc_data, subscription_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for Azure Storage Account {acc_data.name}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    resource_id=acc_data.id,
                    resource_type="AzureStorageAccount",
                    account_id=subscription_id or "N/A",
                    region=acc_data.location,
                    provider="azure",
                    severity="Medium",
                    title=f"Erro ao Avaliar Política de Storage {policy.policy_id}",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para a Storage Account Azure {acc_data.name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR_AZURE_STORAGE",
                    details={"failed_policy_id": policy.policy_id, "storage_account_name": acc_data.name, "error": str(e)},
                    recommendation="Verifique os logs do Policy Engine para mais detalhes e a estrutura dos dados de entrada."
                ))

    logger.info(f"Avaliação de Azure Storage Accounts concluída para a subscrição {subscription_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts
