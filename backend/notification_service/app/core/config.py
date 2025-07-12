import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any

# --- Configurações não-secretas ---
class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "NotificationService"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    RELOAD_UVICORN: bool = False
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Serviço para envio de notificações e alertas."

    # Configs não-secretas de email
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = "CSPMEXA Notification"
    DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL: Optional[str] = None

    # Endereço do Vault
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True

# --- Lógica de Carregamento do Vault ---

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
    vault_token = os.getenv("VAULT_TOKEN")
    if not vault_token:
        print("AVISO: VAULT_TOKEN não encontrado.")
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
        smtp_secrets = client.secrets.kv.v2.read_secret_version(path='smtp')
        smtp_data = smtp_secrets['data']['data']
        secrets['SMTP_HOST'] = smtp_data.get('host')
        secrets['SMTP_PORT'] = int(smtp_data.get('port', 587))
        secrets['SMTP_USER'] = smtp_data.get('user')
        secrets['SMTP_PASSWORD'] = smtp_data.get('password')
        secrets['SMTP_TLS'] = smtp_data.get('tls', 'true').lower() in ('true', '1', 't')
        secrets['SMTP_SSL'] = smtp_data.get('ssl', 'false').lower() in ('true', '1', 't')
    except Exception as e:
        print(f"ERRO: Falha ao carregar segredos de SMTP do Vault. Erro: {e}")
        raise e
    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    # Campos que serão preenchidos pelo Vault
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
        print("Conectado ao Vault. Carregando segredos para NotificationService...")
        vault_secrets = load_secrets_from_vault(vault_client)
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        print("AVISO: Não foi possível carregar a configuração do Vault para NotificationService.")

    # Validação
    if not settings.EMAILS_FROM_EMAIL:
        print("AVISO: EMAILS_FROM_EMAIL não está configurado.")

    return settings

settings = get_settings()
