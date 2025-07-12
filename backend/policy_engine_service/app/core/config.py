import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any

# --- Configurações não-secretas ---
class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "PolicyEngineService"
    API_V1_STR: str = "/api/v1"

    # URL do Notification Service
    NOTIFICATION_SERVICE_URL: str = "http://notification_service:8003/api/v1"

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
        db_secrets = client.secrets.kv.v2.read_secret_version(path='database')
        db_data = db_secrets['data']['data']
        secrets['DATABASE_URL'] = f"postgresql://{db_data['user']}:{db_data['password']}@postgres_auth_db:5432/cspmexa_db"
    except Exception as e:
        print(f"ERRO: Falha ao carregar segredos de DB do Vault. Erro: {e}")
        raise e
    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    # Campo que será preenchido pelo Vault
    DATABASE_URL: Optional[str] = None

@lru_cache()
def get_settings() -> AppSettings:
    settings = AppSettings()
    vault_client = get_vault_client()
    if vault_client:
        print("Conectado ao Vault. Carregando segredos para PolicyEngineService...")
        vault_secrets = load_secrets_from_vault(vault_client)
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        print("AVISO: Não foi possível carregar a configuração do Vault para PolicyEngineService.")

    if not settings.DATABASE_URL:
        raise ValueError("Configuração crítica DATABASE_URL não foi carregada. Abortando.")

    return settings

settings = get_settings()
