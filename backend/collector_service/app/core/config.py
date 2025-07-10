from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "CollectorService"
    API_V1_STR: str = "/api/v1"

    # AWS Settings (opcional, pode ser configurado via variáveis de ambiente do Boto3)
    AWS_REGION_NAME: str = (
        "us-east-1"  # Região padrão para algumas operações globais ou se não especificado
    )
    # AWS_ACCESS_KEY_ID: Optional[str] = None
    # AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # GCP Settings - A autenticação é via GOOGLE_APPLICATION_CREDENTIALS (variável de ambiente)
    # GCP_PROJECT_ID: Optional[str] = None # Pode ser fornecido via API ou configurado aqui como default

    # Huawei Cloud Settings
    # HUAWEICLOUD_SDK_AK: Optional[str] = None
    # HUAWEICLOUD_SDK_SK: Optional[str] = None
    # HUAWEICLOUD_SDK_PROJECT_ID: Optional[str] = None # Project ID para escopo de recursos
    # HUAWEICLOUD_SDK_DOMAIN_ID: Optional[str] = None # Domain ID (Account ID) para IAM

    # Azure Settings
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None


    class Config:
        case_sensitive = True
        # Pydantic v2 usaria model_config em vez de Config
        # Pydantic v1:
        # Para Pydantic v1, se você quiser carregar de .env automaticamente para a classe Settings:
        # env_file = ".env"
        # env_file_encoding = "utf-8"
        # Para Pydantic v2, seria:
        # model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
        # No entanto, o .env é geralmente carregado por python-dotenv no main.py ou globalmente.
        # Pydantic-settings lerá automaticamente as variáveis de ambiente.

from typing import Optional # Adicionar import Optional

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
