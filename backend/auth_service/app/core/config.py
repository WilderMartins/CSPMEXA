import os
import hvac
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Dict, Any

# --- Configurações não-secretas ---
# Estas são carregadas de variáveis de ambiente e não são consideradas segredos.
class BaseAppSettings(BaseSettings):
    PROJECT_NAME: str = "AuthService"
    API_V1_STR: str = "/api/v1"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia
    TOTP_ISSUER_NAME: str = "CSPMEXA"

    # URLs para redirecionamento do frontend
    FRONTEND_URL_AUTH_CALLBACK: str = "http://localhost:3000/auth/callback"
    FRONTEND_URL_MFA_SETUP: str = "http://localhost:3000/mfa-setup"
    FRONTEND_URL_MFA_REQUIRED: str = "http://localhost:3000/mfa-login"

    # Endereço do Vault, injetado via variável de ambiente
    VAULT_ADDR: str = "http://vault:8200"
    VAULT_TOKEN: Optional[str] = None # O token será injetado no ambiente do container

    class Config:
        case_sensitive = True
        env_file = ".env" # Ainda pode ser útil para desenvolvimento local sem Docker
        env_file_encoding = "utf-8"

# --- Lógica de Carregamento de Segredos do Vault ---

@lru_cache()
def get_vault_client() -> Optional[hvac.Client]:
    """Cria e retorna um cliente HVAC para o Vault."""
    vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
    vault_token = os.getenv("VAULT_TOKEN")

    if not vault_token:
        print("AVISO: VAULT_TOKEN não encontrado. Não será possível carregar segredos do Vault.")
        return None

    try:
        client = hvac.Client(url=vault_addr, token=vault_token)
        if not client.is_authenticated():
            print("ERRO: Falha ao autenticar no Vault com o token fornecido.")
            return None
        return client
    except Exception as e:
        print(f"ERRO: Não foi possível conectar ao Vault em {vault_addr}. Erro: {e}")
        return None

def load_secrets_from_vault(client: hvac.Client) -> Dict[str, Any]:
    """Carrega segredos de diferentes caminhos no Vault."""
    secrets = {}
    try:
        # Carregar segredos do banco de dados
        db_secrets = client.secrets.kv.v2.read_secret_version(path='database')
        db_data = db_secrets['data']['data']
        # Constrói a DATABASE_URL a partir das partes
        secrets['DATABASE_URL'] = f"postgresql://{db_data['user']}:{db_data['password']}@postgres_auth_db:5432/cspmexa_db"

        # Carregar chave JWT
        jwt_secrets = client.secrets.kv.v2.read_secret_version(path='jwt')
        secrets['JWT_SECRET_KEY'] = jwt_secrets['data']['data']['key']

        # Carregar segredos do Google OAuth
        google_secrets = client.secrets.kv.v2.read_secret_version(path='google_oauth')
        google_data = google_secrets['data']['data']
        secrets['GOOGLE_CLIENT_ID'] = google_data.get('client_id')
        secrets['GOOGLE_CLIENT_SECRET'] = google_data.get('client_secret')
        # A URI de redirecionamento pode ser construída ou definida como variável de ambiente se mudar frequentemente
        secrets['GOOGLE_REDIRECT_URI'] = "http://localhost:8050/api/v1/auth/google/callback"

    except Exception as e:
        print(f"ERRO: Falha ao carregar segredos do Vault. Verifique os caminhos e permissões. Erro: {e}")
        # Lançar o erro pode ser melhor para impedir que a aplicação inicie sem configuração.
        raise e

    return secrets

# --- Objeto de Configuração Final ---

class AppSettings(BaseAppSettings):
    # Campos que serão preenchidos pelo Vault
    DATABASE_URL: Optional[str] = None
    JWT_SECRET_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

@lru_cache()
def get_settings() -> AppSettings:
    """
    Cria a configuração final, combinando variáveis de ambiente com segredos do Vault.
    """
    # 1. Carrega configurações base (não-secretas) do ambiente
    settings = AppSettings()

    # 2. Conecta ao Vault e carrega segredos
    vault_client = get_vault_client()
    if vault_client:
        print("Conectado ao Vault. Carregando segredos...")
        vault_secrets = load_secrets_from_vault(vault_client)

        # 3. Atualiza o objeto de settings com os segredos carregados
        for key, value in vault_secrets.items():
            setattr(settings, key, value)
    else:
        print("AVISO: Não foi possível carregar a configuração do Vault. A aplicação pode não funcionar corretamente.")

    # Validação final para garantir que segredos críticos foram carregados
    if not settings.DATABASE_URL or not settings.JWT_SECRET_KEY:
        raise ValueError("Configurações críticas (DATABASE_URL, JWT_SECRET_KEY) não foram carregadas. Abortando.")

    return settings

# Instância global das configurações, acessível em toda a aplicação
settings = get_settings()
