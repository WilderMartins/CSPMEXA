import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any
import logging

# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configurações não-secretas ---
class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "AuthService"
    API_V1_STR: str = "/api/v1"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    TOTP_ISSUER_NAME: str = "CSPMEXA"
    FRONTEND_URL_AUTH_CALLBACK: str = "http://localhost:3000/auth/callback"
    FRONTEND_URL_MFA_SETUP: str = "http://localhost:3000/mfa-setup"
    FRONTEND_URL_MFA_REQUIRED: str = "http://localhost:3000/mfa-login"
    VAULT_ADDR: str = "http://vault:8200"

    # Variáveis para AppRole (não são segredos, são identificadores)
    VAULT_ROLE_ID: Optional[str] = None
    VAULT_SECRET_ID: Optional[str] = None # Este É um segredo, mas é lido do ambiente

    # Fallback para token (para desenvolvimento local sem AppRole)
    VAULT_TOKEN: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# --- Lógica de Carregamento de Segredos do Vault ---

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    """Cria e autentica um cliente HVAC para o Vault usando AppRole."""
    settings = BaseAppSettings()
    client = hvac.Client(url=settings.VAULT_ADDR)

    try:
        if settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
            logger.info("Tentando autenticação no Vault via AppRole...")
            client.auth.approle.login(
                role_id=settings.VAULT_ROLE_ID,
                secret_id=settings.VAULT_SECRET_ID,
            )
        elif settings.VAULT_TOKEN:
            logger.warning("Autenticando no Vault com VAULT_TOKEN. Recomendado usar AppRole.")
            client.token = settings.VAULT_TOKEN
        else:
            logger.error("Credenciais do Vault (AppRole ou Token) não encontradas.")
            return None

        if not client.is_authenticated():
            logger.error("Falha ao autenticar no Vault.")
            return None

        logger.info("Autenticação no Vault bem-sucedida.")
        return client

    except Exception as e:
        logger.error(f"Não foi possível conectar ou autenticar no Vault em {settings.VAULT_ADDR}. Erro: {e}")
        return None

def load_secrets_from_vault(client: hvac.Client) -> Dict[str, Any]:
    """Carrega segredos de diferentes caminhos no Vault."""
    secrets = {}
    try:
        logger.info("Carregando segredos do path 'secret/database'...")
        db_secrets = client.secrets.kv.v2.read_secret_version(path='database')
        db_data = db_secrets['data']['data']
        secrets['DATABASE_URL'] = f"postgresql://{db_data['user']}:{db_data['password']}@postgres_auth_db:5432/cspmexa_db"

        logger.info("Carregando segredos do path 'secret/jwt'...")
        jwt_secrets = client.secrets.kv.v2.read_secret_version(path='jwt')
        secrets['JWT_SECRET_KEY'] = jwt_secrets['data']['data']['key']

        logger.info("Carregando segredos do path 'secret/google_oauth'...")
        google_secrets = client.secrets.kv.v2.read_secret_version(path='google_oauth')
        google_data = google_secrets['data']['data']
        secrets['GOOGLE_CLIENT_ID'] = google_data.get('client_id')
        secrets['GOOGLE_CLIENT_SECRET'] = google_data.get('client_secret')
        secrets['GOOGLE_REDIRECT_URI'] = "http://localhost:8050/api/v1/auth/google/callback"

        logger.info("Segredos carregados com sucesso.")

    except Exception as e:
        logger.error(f"Falha ao carregar segredos do Vault. Verifique os caminhos e permissões. Erro: {e}")
        raise e

    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    DATABASE_URL: Optional[str] = None
    JWT_SECRET_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

@lru_cache()
def get_settings() -> AppSettings:
    """Cria a configuração final, combinando variáveis de ambiente com segredos do Vault."""
    settings = AppSettings()
    vault_client = get_vault_client()

    if vault_client:
        logger.info("Cliente do Vault autenticado. Carregando segredos...")
        vault_secrets = load_secrets_from_vault(vault_client)
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        logger.error("Não foi possível carregar a configuração do Vault. A aplicação pode não funcionar.")

    if not settings.DATABASE_URL or not settings.JWT_SECRET_KEY:
        raise ValueError("Configurações críticas (DATABASE_URL, JWT_SECRET_KEY) não foram carregadas. Abortando.")

    return settings

# Instância global das configurações
settings = get_settings()
