import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "CollectorService"
    API_V1_STR: str = "/api/v1"
    AWS_REGION_NAME: str = "us-east-1"
    VAULT_ADDR: str = "http://vault:8200"

    # AppRole
    VAULT_ROLE_ID: Optional[str] = None
    VAULT_SECRET_ID: Optional[str] = None

    # Fallback
    VAULT_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    """Cria e autentica um cliente HVAC para o Vault usando AppRole."""
    client = hvac.Client(url=settings.VAULT_ADDR)
    try:
        if settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
            logger.info("Tentando autenticação no Vault via AppRole para CollectorService...")
            client.auth.approle.login(
                role_id=settings.VAULT_ROLE_ID,
                secret_id=settings.VAULT_SECRET_ID,
            )
        elif settings.VAULT_TOKEN:
            logger.warning("Autenticando no Vault com VAULT_TOKEN no CollectorService.")
            client.token = settings.VAULT_TOKEN
        else:
            logger.error("Credenciais do Vault (AppRole ou Token) não encontradas no CollectorService.")
            return None

        if not client.is_authenticated():
            logger.error("Falha ao autenticar no Vault no CollectorService.")
            return None

        logger.info("Autenticação no Vault bem-sucedida no CollectorService.")
        return client

    except Exception as e:
        logger.error(f"Não foi possível conectar ou autenticar no Vault no CollectorService. Erro: {e}")
        return None

def get_credentials_from_vault(provider: str) -> Optional[Dict[str, Any]]:
    """Busca as credenciais para um provedor específico do Vault."""
    client = get_vault_client()
    if not client:
        logger.warning(f"Cliente do Vault não disponível. Não é possível buscar credenciais para {provider}.")
        return None

    path = f"{provider}_credentials"
    logger.info(f"Buscando credenciais para '{provider}' do Vault no path 'secret/{path}'...")
    try:
        response = client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
    except Exception as e:
        logger.warning(f"Falha ao buscar credenciais para '{provider}' do Vault. Erro: {e}")
        return None
