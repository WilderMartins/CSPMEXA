import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppSettings(BaseSettings):
    """
    Carrega as configurações do NotificationService a partir de variáveis de ambiente.
    O vault-agent injeta os segredos em um arquivo .env que é carregado no ambiente.
    """
    PROJECT_NAME: str = "NotificationService"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    RELOAD_UVICORN: bool = False
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Serviço para envio de notificações e alertas."

    # Configurações de e-mail (injetadas pelo Vault ou do .env principal)
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = "CSPMEXA Notification"
    DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL: Optional[str] = None

    # Configurações SMTP (injetadas pelo Vault)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> AppSettings:
    logger.info("Carregando configurações para NotificationService...")
    try:
        settings = AppSettings()
        if not settings.EMAILS_FROM_EMAIL:
            logger.warning("EMAILS_FROM_EMAIL não está configurado.")
        logger.info("Configurações do NotificationService carregadas com sucesso.")
        return settings
    except Exception as e:
        logger.error(f"Erro ao carregar configurações do NotificationService: {e}")
        raise

settings = get_settings()
