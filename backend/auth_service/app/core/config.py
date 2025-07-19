import os
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

    class Config:
        case_sensitive = True
        # Pydantic-settings carrega automaticamente do ambiente.
        # O script de inicialização do contêiner (no docker-compose)
        # carrega o /vault/secrets/auth-secrets.env para o ambiente.
        env_file = ".env" # Pode ainda ser usado para configs não-secretas
        env_file_encoding = "utf-8"

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

# Instância global das configurações
settings = get_settings()
