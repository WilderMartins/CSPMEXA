from pydantic_settings import BaseSettings
from functools import lru_cache
# from typing import Optional # Removido


class Settings(BaseSettings):
    PROJECT_NAME: str = "APIGatewayService"
    API_V1_STR: str = "/api/v1"  # Prefixo para os endpoints do gateway em si

    # URLs dos serviços downstream
    AUTH_SERVICE_URL: str = "http://localhost:8000/api/v1"  # Porta do auth-service
    COLLECTOR_SERVICE_URL: str = (
        "http://localhost:8001/api/v1"  # Porta do collector-service
    )
    POLICY_ENGINE_SERVICE_URL: str = (
        "http://localhost:8002/api/v1"  # Porta do policy-engine-service
    )

    # JWT Secret para validação (deve ser o mesmo do auth-service)
    # Se a validação for delegada ao auth-service, isso não é estritamente necessário aqui,
    # mas pode ser útil para decodificar o token para obter user_id sem chamar o auth-service toda vez.
    JWT_SECRET_KEY: str = (
        "super-secret-key"  # Mudar isso e carregar de .env (mesmo do auth-service)
    )
    JWT_ALGORITHM: str = "HS256"  # Mesmo do auth-service

    # Timeout para chamadas HTTP aos serviços downstream (em segundos)
    HTTP_CLIENT_TIMEOUT: int = 30

    # Chave de API para comunicação interna segura entre serviços
    INTERNAL_API_KEY: str = "change-this-in-production"

    # Configurações específicas de provedores que o Gateway pode precisar
    # Ex: Tenant ID padrão para M365 se não vier do frontend ou de outro lugar
    M365_TENANT_ID: Optional[str] = None # Carregar de .env

    class Config:
        case_sensitive = True
        # env_file = ".env" # Para desenvolvimento local, carregar de .env
        # env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
