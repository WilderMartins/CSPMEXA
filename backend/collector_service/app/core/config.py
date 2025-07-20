import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Carrega as configurações do CollectorService a partir de variáveis de ambiente.
    O vault-agent injeta os segredos em um arquivo .env que é carregado no ambiente.
    """
    PROJECT_NAME: str = "CollectorService"
    API_V1_STR: str = "/api/v1"

    # Credenciais e configurações (a maioria virá do Vault)
    AWS_REGION_NAME: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None

    GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL: Optional[str] = None

    HUAWEICLOUD_SDK_AK: Optional[str] = None
    HUAWEICLOUD_SDK_SK: Optional[str] = None
    HUAWEICLOUD_SDK_PROJECT_ID: Optional[str] = None
    HUAWEICLOUD_SDK_DOMAIN_ID: Optional[str] = None

    M365_CLIENT_ID: Optional[str] = None
    M365_CLIENT_SECRET: Optional[str] = None
    M365_TENANT_ID: Optional[str] = None

    # Caminhos para arquivos de credenciais que ainda são montados como volumes
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = "/app/secrets/gcp-credentials.json"
    GOOGLE_SERVICE_ACCOUNT_KEY_PATH: Optional[str] = "/app/secrets/gws-sa-key.json"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    logger.info("Carregando configurações para CollectorService...")
    try:
        settings = Settings()
        logger.info("Configurações do CollectorService carregadas com sucesso.")
        return settings
    except Exception as e:
        logger.error(f"Erro ao carregar configurações do CollectorService: {e}")
        raise

settings = get_settings()
