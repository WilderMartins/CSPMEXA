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

# Tentar carregar as configurações do settings do collector_service se existir
# Se não, carregar diretamente das variáveis de ambiente.
try:
    AZURE_SUBSCRIPTION_ID = settings.AZURE_SUBSCRIPTION_ID
    AZURE_TENANT_ID = settings.AZURE_TENANT_ID
    AZURE_CLIENT_ID = settings.AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET = settings.AZURE_CLIENT_SECRET
except AttributeError: # Fallback para os.environ se settings não tiver as vars Azure
    logger.info("Azure settings not found in app.core.config.settings, trying os.environ.")
    AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")


def get_azure_credentials():
    """
    Obtém as credenciais do Azure.
    Prioriza ClientSecretCredential se todas as variáveis estiverem definidas,
    caso contrário, usa DefaultAzureCredential.
    """
    if AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET:
        logger.info("Using ClientSecretCredential for Azure.")
        return ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
    else:
        logger.info("Client secret credentials not fully provided, attempting DefaultAzureCredential.")
        # DefaultAzureCredential tentará várias estratégias (env vars, Azure CLI, Managed Identity etc.)
        # Certifique-se de que as variáveis de ambiente AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
        # são lidas pelo DefaultAzureCredential se este for o método desejado sem ClientSecretCredential explícito.
        # Ou que o ambiente de execução (ex: VM com Managed Identity, Azure CLI logada) está configurado.
        return DefaultAzureCredential()

@lru_cache(maxsize=5) # Cache para evitar recriar clientes para a mesma subscrição
def get_compute_management_client(subscription_id: str = None) -> ComputeManagementClient:
    sub_id = subscription_id or AZURE_SUBSCRIPTION_ID
    if not sub_id:
        raise ValueError("Azure Subscription ID is required to create ComputeManagementClient.")
    credential = get_azure_credentials()
    logger.debug(f"Creating ComputeManagementClient for subscription ID: {sub_id}")
    return ComputeManagementClient(credential=credential, subscription_id=sub_id)

@lru_cache(maxsize=5)
def get_storage_management_client(subscription_id: str = None) -> StorageManagementClient:
    sub_id = subscription_id or AZURE_SUBSCRIPTION_ID
    if not sub_id:
        raise ValueError("Azure Subscription ID is required to create StorageManagementClient.")
    credential = get_azure_credentials()
    logger.debug(f"Creating StorageManagementClient for subscription ID: {sub_id}")
    return StorageManagementClient(credential=credential, subscription_id=sub_id)

@lru_cache(maxsize=5)
def get_resource_management_client(subscription_id: str = None) -> ResourceManagementClient:
    sub_id = subscription_id or AZURE_SUBSCRIPTION_ID
    if not sub_id:
        raise ValueError("Azure Subscription ID is required to create ResourceManagementClient.")
    credential = get_azure_credentials()
    logger.debug(f"Creating ResourceManagementClient for subscription ID: {sub_id}")
    return ResourceManagementClient(credential=credential, subscription_id=sub_id)

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
