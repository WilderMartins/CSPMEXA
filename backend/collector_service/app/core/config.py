from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "CollectorService"
    API_V1_STR: str = "/api/v1"

    # AWS Settings (opcional, pode ser configurado via variáveis de ambiente do Boto3)
    AWS_REGION_NAME: str = (
        "us-east-1"  # Região padrão para algumas operações globais ou se não especificado
    )
    # AWS_ACCESS_KEY_ID: str = "YOUR_AWS_ACCESS_KEY_ID" # Idealmente via env vars ou instance profile
    # AWS_SECRET_ACCESS_KEY: str = "YOUR_AWS_SECRET_ACCESS_KEY" # Idealmente via env vars ou instance profile

    class Config:
        case_sensitive = True
        # env_file = ".env"
        # env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
