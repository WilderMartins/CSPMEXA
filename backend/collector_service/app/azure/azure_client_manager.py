import os
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.resource import ResourceManagementClient
from app.core.config import settings # Supondo que o collector_service tem um config similar
                                     # ou que vamos ler diretamente do os.environ
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Utiliza as configurações carregadas de app.core.config.settings
# que por sua vez lê variáveis de ambiente ou .env.

def get_azure_credentials():
    """
    Obtém as credenciais do Azure.
    Prioriza ClientSecretCredential se todas as variáveis (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
    estiverem definidas em settings. Caso contrário, usa DefaultAzureCredential.
    """
    if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET:
        logger.info("Using ClientSecretCredential for Azure based on explicit settings.")
        return ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        )
    else:
        logger.info("Client secret credentials not fully provided in settings, attempting DefaultAzureCredential.")
        # DefaultAzureCredential tentará várias estratégias (env vars AZURE_*, Azure CLI, Managed Identity etc.)
        return DefaultAzureCredential()

@lru_cache(maxsize=5) # Cache para evitar recriar clientes para a mesma subscrição
def get_compute_management_client(subscription_id: str = None) -> ComputeManagementClient:
    # Prioriza o subscription_id passado como argumento, depois o de settings.
    sub_id_to_use = subscription_id or settings.AZURE_SUBSCRIPTION_ID
    if not sub_id_to_use:
        raise ValueError("Azure Subscription ID is required to create ComputeManagementClient. Provide it as an argument or set AZURE_SUBSCRIPTION_ID in settings/env.")
    credential = get_azure_credentials()
    logger.debug(f"Creating ComputeManagementClient for subscription ID: {sub_id_to_use}")
    return ComputeManagementClient(credential=credential, subscription_id=sub_id_to_use)

@lru_cache(maxsize=5)
def get_storage_management_client(subscription_id: str = None) -> StorageManagementClient:
    sub_id_to_use = subscription_id or settings.AZURE_SUBSCRIPTION_ID
    if not sub_id_to_use:
        raise ValueError("Azure Subscription ID is required to create StorageManagementClient. Provide it as an argument or set AZURE_SUBSCRIPTION_ID in settings/env.")
    credential = get_azure_credentials()
    logger.debug(f"Creating StorageManagementClient for subscription ID: {sub_id_to_use}")
    return StorageManagementClient(credential=credential, subscription_id=sub_id_to_use)

@lru_cache(maxsize=5)
def get_resource_management_client(subscription_id: str = None) -> ResourceManagementClient:
    sub_id_to_use = subscription_id or settings.AZURE_SUBSCRIPTION_ID
    if not sub_id_to_use:
        raise ValueError("Azure Subscription ID is required to create ResourceManagementClient. Provide it as an argument or set AZURE_SUBSCRIPTION_ID in settings/env.")
    credential = get_azure_credentials()
    logger.debug(f"Creating ResourceManagementClient for subscription ID: {sub_id_to_use}")
    return ResourceManagementClient(credential=credential, subscription_id=sub_id_to_use)

# Exemplo de como obter um cliente:
# compute_client = get_compute_management_client()
# storage_client = get_storage_management_client(" outra-subscricao-id")
# resource_client = get_resource_management_client()

# Criar __init__.py na pasta azure
# mkdir -p backend/collector_service/app/azure/
# touch backend/collector_service/app/azure/__init__.py
# Isso já deve ter sido feito implicitamente pela criação do arquivo acima,
# mas é bom garantir.
# O `settings` importado de `app.core.config` precisa ser ajustado.
# O collector_service já tem um `app/core/config.py`.
# Vamos verificar se ele já carrega essas variáveis ou precisa ser atualizado.
# Por agora, o fallback para `os.environ` deve funcionar se `settings` não as tiver.
