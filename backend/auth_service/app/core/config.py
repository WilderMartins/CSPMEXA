import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import logging

# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppSettings(BaseSettings):
    """
    Carrega as configurações da aplicação a partir de variáveis de ambiente.
    O vault-agent é responsável por injetar os segredos em um arquivo .env,
    que é lido por esta classe.
    """
    PROJECT_NAME: str = "AuthService"
    API_V1_STR: str = "/api/v1"

    # Configurações do Banco de Dados (ainda podem vir do .env principal)
    DATABASE_URL: str

    # Segredos injetados pelo Vault Agent
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Configurações do Google OAuth (injetadas ou do .env principal)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = "http://localhost:8050/api/v1/auth/google/callback"

    # Configurações de MFA
    TOTP_ISSUER_NAME: str = "CSPMEXA"

    # URLs do Frontend
    FRONTEND_URL_AUTH_CALLBACK: str = "http://localhost:3000/auth/callback"
    FRONTEND_URL_MFA_SETUP: str = "http://localhost:3000/mfa-setup"
    FRONTEND_URL_MFA_REQUIRED: str = "http://localhost:3000/mfa-login"

    # Configurações do Vault (para o credentials_service)
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_ROLE_ID: Optional[str] = None
    VAULT_SECRET_ID: Optional[str] = None

    # URL do serviço de auditoria
    AUDIT_SERVICE_URL: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> AppSettings:
    """
    Retorna uma instância cacheada das configurações da aplicação.
    """
    logger.info("Carregando configurações da aplicação...")
    try:
        settings = AppSettings()
        logger.info("Configurações carregadas com sucesso.")
        return settings
    except Exception as e:
        logger.error(f"Erro ao carregar as configurações: {e}")
        raise

settings = get_settings()

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    """
    Cria e autentica um cliente HVAC para o Vault.
    Esta função é usada especificamente pelo credentials_service.
    """
    client = hvac.Client(url=settings.VAULT_ADDR)
    try:
        if settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
            client.auth.approle.login(
                role_id=settings.VAULT_ROLE_ID,
                secret_id=settings.VAULT_SECRET_ID,
            )
            if client.is_authenticated():
                logger.info("Cliente do Vault autenticado com sucesso via AppRole para o credentials_service.")
                return client
    except Exception as e:
        logger.error(f"Falha ao autenticar no Vault com AppRole para o credentials_service: {e}")

    logger.warning("Não foi possível autenticar no Vault com AppRole. O credentials_service pode não funcionar.")
    return None
