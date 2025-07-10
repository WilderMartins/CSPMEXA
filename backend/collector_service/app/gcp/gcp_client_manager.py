import google.auth
from google.cloud import asset_v1
from google.cloud import storage
from google.cloud import compute_v1
from googleapiclient.discovery import build as discovery_build # Para Cloud Resource Manager
from app.core.config import settings # Para obter PROJECT_ID, se configurado lá
import logging

logger = logging.getLogger(__name__)

# Cache para os clientes, para evitar recriação a cada chamada
_clients_cache = {}

def get_gcp_project_id() -> str:
    """
    Obtém o Project ID do GCP.
    Primeiro tenta das credenciais, depois de uma variável de ambiente específica,
    e por último de settings (se configurado).
    """
    try:
        _, project_id = google.auth.default()
        if project_id:
            return project_id
    except Exception as e:
        logger.debug(f"Could not get project ID from google.auth.default(): {e}")

    # Tentar de settings (se você adicionar GCP_PROJECT_ID a Settings)
    # gcp_project_id_from_settings = getattr(settings, "GCP_PROJECT_ID", None)
    # if gcp_project_id_from_settings:
    #     return gcp_project_id_from_settings

    # Levantar um erro se não conseguir determinar o ID do projeto
    # Isso é crucial para a maioria das chamadas de API.
    # O chamador precisará lidar com isso ou garantir que está configurado.
    # No contexto do collector, o project_id pode vir na requisição ou ser global.
    # Para agora, vamos assumir que ele precisa ser descoberto ou configurado.
    # Se não for encontrado, as funções de coleta precisarão de um project_id explícito.
    logger.warning("GCP Project ID could not be determined automatically. Ensure GOOGLE_APPLICATION_CREDENTIALS is set or project is explicitly provided.")
    return None # Ou levantar uma exceção


def get_asset_client() -> asset_v1.AssetServiceClient:
    """Retorna um cliente para o Cloud Asset Inventory API."""
    if "asset" not in _clients_cache:
        try:
            _clients_cache["asset"] = asset_v1.AssetServiceClient()
            logger.info("Cloud Asset Inventory client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Asset Inventory client: {e}")
            raise
    return _clients_cache["asset"]

def get_storage_client(project_id: str = None) -> storage.Client:
    """Retorna um cliente para o Cloud Storage API."""
    # O cliente de storage pode ser inicializado com um projeto específico ou usar o padrão das credenciais.
    client_key = f"storage_{project_id or 'default'}"
    if client_key not in _clients_cache:
        try:
            if project_id:
                _clients_cache[client_key] = storage.Client(project=project_id)
            else:
                _clients_cache[client_key] = storage.Client() # Usa o projeto das credenciais
            logger.info(f"Cloud Storage client initialized for project '{project_id or 'default'}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage client: {e}")
            raise
    return _clients_cache[client_key]

def get_compute_client() -> compute_v1.InstancesClient: # Ou outros clientes compute como FirewallsClient
    """Retorna um cliente para o Compute Engine API (InstancesClient)."""
    if "compute_instances" not in _clients_cache:
        try:
            _clients_cache["compute_instances"] = compute_v1.InstancesClient()
            logger.info("Compute Engine Instances client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Compute Engine Instances client: {e}")
            raise
    return _clients_cache["compute_instances"]

def get_compute_firewalls_client() -> compute_v1.FirewallsClient:
    """Retorna um cliente para o Compute Engine API (FirewallsClient)."""
    if "compute_firewalls" not in _clients_cache:
        try:
            _clients_cache["compute_firewalls"] = compute_v1.FirewallsClient()
            logger.info("Compute Engine Firewalls client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Compute Engine Firewalls client: {e}")
            raise
    return _clients_cache["compute_firewalls"]


def get_cloud_resource_manager_client(): # type: ignore
    """Retorna um cliente para o Cloud Resource Manager API (v1 ou v3)."""
    # Esta API é mais antiga e usa googleapiclient.discovery
    # Pode ser necessário especificar a versão (v1, v3)
    # As credenciais ADC devem funcionar aqui também.
    if "cloudresourcemanager" not in _clients_cache:
        try:
            # Tentar v3 primeiro, pois é mais recente
            _clients_cache["cloudresourcemanager"] = discovery_build('cloudresourcemanager', 'v3')
            logger.info("Cloud Resource Manager v3 client initialized.")
        except Exception as e_v3:
            logger.warning(f"Failed to initialize Cloud Resource Manager v3 client: {e_v3}. Trying v1.")
            try:
                _clients_cache["cloudresourcemanager"] = discovery_build('cloudresourcemanager', 'v1')
                logger.info("Cloud Resource Manager v1 client initialized.")
            except Exception as e_v1:
                logger.error(f"Failed to initialize Cloud Resource Manager v1 client: {e_v1}")
                raise
    return _clients_cache["cloudresourcemanager"]


# Exemplo de como obter credenciais e o projeto padrão (pode ser útil em coletores)
def get_default_credentials_and_project():
    try:
        credentials, project = google.auth.default()
        return credentials, project
    except Exception as e:
        logger.error(f"Could not load default GCP credentials: {e}")
        return None, None

if __name__ == '__main__':
    # Pequeno teste para verificar se os clientes podem ser inicializados (requer GOOGLE_APPLICATION_CREDENTIALS setado)
    print(f"Attempting to get default project ID: {get_gcp_project_id()}")
    try:
        get_asset_client()
        get_storage_client()
        get_compute_client()
        get_compute_firewalls_client()
        get_cloud_resource_manager_client()
        print("All GCP clients seem to initialize (superficially).")
    except Exception as e:
        print(f"Error during client initialization test: {e}")
