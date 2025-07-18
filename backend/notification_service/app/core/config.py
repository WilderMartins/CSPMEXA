import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configurações não-secretas ---
class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "NotificationService"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    RELOAD_UVICORN: bool = False
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Serviço para envio de notificações e alertas."
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = "CSPMEXA Notification"
    DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL: Optional[str] = None
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

# --- Lógica de Carregamento do Vault ---

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    """Cria e autentica um cliente HVAC para o Vault usando AppRole."""
    settings = BaseAppSettings()
    client = hvac.Client(url=settings.VAULT_ADDR)
    try:
        if settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
            logger.info("Tentando autenticação no Vault via AppRole para NotificationService...")
            client.auth.approle.login(
                role_id=settings.VAULT_ROLE_ID,
                secret_id=settings.VAULT_SECRET_ID,
            )
        elif settings.VAULT_TOKEN:
            logger.warning("Autenticando no Vault com VAULT_TOKEN no NotificationService.")
            client.token = settings.VAULT_TOKEN
        else:
            logger.error("Credenciais do Vault (AppRole ou Token) não encontradas no NotificationService.")
            return None

        if not client.is_authenticated():
            logger.error("Falha ao autenticar no Vault no NotificationService.")
            return None

        logger.info("Autenticação no Vault bem-sucedida no NotificationService.")
        return client

    except Exception as e:
        logger.error(f"Não foi possível conectar ou autenticar no Vault no NotificationService. Erro: {e}")
        return None

def load_secrets_from_vault(client: hvac.Client) -> Dict[str, Any]:
    """Carrega segredos de SMTP do Vault."""
    secrets = {}
    logger.info("Carregando segredos de SMTP do Vault...")
    try:
        smtp_secrets = client.secrets.kv.v2.read_secret_version(path='smtp')
        smtp_data = smtp_secrets['data']['data']
        secrets['SMTP_HOST'] = smtp_data.get('host')
        secrets['SMTP_PORT'] = int(smtp_data.get('port', 587))
        secrets['SMTP_USER'] = smtp_data.get('user')
        secrets['SMTP_PASSWORD'] = smtp_data.get('password')
        secrets['SMTP_TLS'] = smtp_data.get('tls', 'true').lower() in ('true', '1', 't')
        secrets['SMTP_SSL'] = smtp_data.get('ssl', 'false').lower() in ('true', '1', 't')
        logger.info("Segredos de SMTP carregados com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao carregar segredos de SMTP do Vault. Erro: {e}")
        raise e
    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

@lru_cache()
def get_settings() -> AppSettings:
    settings = AppSettings()
    vault_client = get_vault_client()
    if vault_client:
        logger.info("Cliente do Vault autenticado. Carregando segredos para NotificationService...")
        vault_secrets = load_secrets_from_vault(vault_client)
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        logger.warning("Não foi possível carregar a configuração do Vault para NotificationService.")

    if not settings.EMAILS_FROM_EMAIL:
        logger.warning("EMAILS_FROM_EMAIL não está configurado.")

    return settings

settings = get_settings()
