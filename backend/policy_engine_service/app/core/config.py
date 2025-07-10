from pydantic_settings import BaseSettings
from functools import lru_cache


import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis de .env para o ambiente

class Settings(BaseSettings):
    PROJECT_NAME: str = "PolicyEngineService"
    API_V1_STR: str = "/api/v1"

    # Configurações do Banco de Dados para Alertas
    ALERT_DATABASE_URL: Optional[str] = None # Permitir override completo da URL
    AUTH_DB_HOST: str = os.getenv("AUTH_DB_HOST", "localhost")
    AUTH_DB_PORT: str = os.getenv("AUTH_DB_PORT", "5432")
    AUTH_DB_USER: str = os.getenv("AUTH_DB_USER", "user")
    AUTH_DB_PASSWORD: str = os.getenv("AUTH_DB_PASSWORD", "password")
    AUTH_DB_NAME: str = os.getenv("AUTH_DB_NAME", "authdb_mvp")

    @property
    def ASSEMBLED_ALERT_DATABASE_URL(self) -> str:
        if self.ALERT_DATABASE_URL:
            return self.ALERT_DATABASE_URL
        # Fallback para montar a URL a partir das partes, se AUTH_DB_* estiverem definidos
        user = self.AUTH_DB_USER
        password = self.AUTH_DB_PASSWORD
        host = self.AUTH_DB_HOST
        port = self.AUTH_DB_PORT
        db_name = self.AUTH_DB_NAME
        if all([user, password, host, port, db_name]):
             return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        raise ValueError("ALERT_DATABASE_URL is not set and cannot be assembled from AUTH_DB_* parts.")


    class Config:
        case_sensitive = True
        # Se você quiser que Pydantic leia diretamente do .env sem load_dotenv()
        # env_file = ".env"
        # env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
