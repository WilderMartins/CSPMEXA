import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "CollectorService"
    API_V1_STR: str = "/api/v1"

    # Configurações não-secretas
    AWS_REGION_NAME: str = "us-east-1"

    # Endereço do Vault
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True

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
        print(f"ERRO: Não foi possível conectar ao Vault no CollectorService. Erro: {e}")
    return None

def get_credentials_from_vault(provider: str) -> Optional[Dict[str, Any]]:
    """Busca as credenciais para um provedor específico do Vault."""
    client = get_vault_client()
    if not client:
        print(f"AVISO: Cliente do Vault não disponível. Não é possível buscar credenciais para {provider}.")
        return None

    path = f"{provider}_credentials"
    try:
        response = client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    except Exception as e:
        print(f"AVISO: Falha ao buscar credenciais para '{provider}' do Vault. Erro: {e}")
        return None

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
