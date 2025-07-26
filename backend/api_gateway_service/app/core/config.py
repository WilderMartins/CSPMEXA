import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any

# --- Configurações não-secretas ---
import os
from pydantic_settings import BaseSettings

class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "APIGatewayService"
    API_V1_STR: str = "/api/v1"

    # URLs dos serviços downstream
    AUTH_SERVICE_URL: str = "http://auth_service:8000/api/v1"
    COLLECTOR_SERVICE_URL: str = "http://collector_service:8001/api/v1"
    POLICY_ENGINE_SERVICE_URL: str = "http://policy_engine_service:8002/api/v1"
    NOTIFICATION_SERVICE_URL: str = "http://notification_service:8003/api/v1"

    JWT_ALGORITHM: str = "HS256"
    HTTP_CLIENT_TIMEOUT: int = 60

    # Endereço do Vault
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True

# --- Lógica de Carregamento do Vault ---

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    if not vault_token:
        return None
    try:
        client = hvac.Client(url=vault_addr, token=vault_token)
        if client.is_authenticated():
            return client
    except Exception as e:
        print(f"ERRO: Não foi possível conectar ao Vault. Erro: {e}")
    return None

def load_secrets_from_vault(client: hvac.Client) -> Dict[str, Any]:
    secrets = {}
    try:
        jwt_secrets = client.secrets.kv.v2.read_secret_version(path='jwt')
        secrets['JWT_SECRET_KEY'] = jwt_secrets['data']['data']['key']
    except Exception as e:
        print(f"ERRO: Falha ao carregar segredo JWT do Vault. Erro: {e}")
        raise e
    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    # Campo que será preenchido pelo Vault
    JWT_SECRET_KEY: Optional[str] = None

@lru_cache()
def get_settings() -> AppSettings:
    if os.getenv("TESTING"):
        return AppSettings(_env_file=".env.test")

    settings = AppSettings()
    vault_client = get_vault_client()
    if vault_client:
        print("Conectado ao Vault. Carregando segredos para APIGatewayService...")
        vault_secrets = load_secrets_from_vault(vault_client)
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        print("AVISO: Não foi possível carregar a configuração do Vault para APIGatewayService.")

    if not settings.JWT_SECRET_KEY:
        raise ValueError("Configuração crítica JWT_SECRET_KEY não foi carregada. Abortando.")

    return settings

settings = get_settings()
