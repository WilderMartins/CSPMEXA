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
    # Configurações do Banco de Dados
    # Para o MVP, vamos assumir que o Policy Engine usará o mesmo banco de dados que o Auth Service.
    # No futuro, isso pode ser um banco de dados separado.
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL") # Definido no .env raiz e passado para os containers

    # As variáveis abaixo são usadas para construir DATABASE_URL se não estiver explicitamente definida.
    # No contexto do Docker Compose, DATABASE_URL será fornecida diretamente.
    DB_HOST: str = os.getenv("AUTH_DB_HOST", "localhost") # Nome do serviço do DB no Docker Compose
    DB_PORT: str = os.getenv("AUTH_DB_PORT", "5432")
    DB_USER: str = os.getenv("AUTH_DB_USER", "user")
    DB_PASSWORD: str = os.getenv("AUTH_DB_PASSWORD", "password")
    DB_NAME: str = os.getenv("AUTH_DB_NAME", "authdb_mvp")

    # URL do Notification Service (para enviar notificações de alerta)
    NOTIFICATION_SERVICE_URL: Optional[str] = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8003/api/v1") # Default para dev local se não vier do compose
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "change-this-in-production")

    @property
    def ASSEMBLED_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        user = self.DB_USER
        password = self.DB_PASSWORD
        host = self.DB_HOST
        port = self.DB_PORT
        db_name = self.DB_NAME

        if all([user, password, host, port, db_name]):
             return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        raise ValueError("DATABASE_URL is not set and cannot be assembled from DB_* parts. Ensure .env is configured.")

    class Config:
        case_sensitive = True
        env_file = os.getenv("ENV_FILE", ".env") # Permite especificar um .env file diferente
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    # load_dotenv() aqui garante que o .env do serviço seja carregado se existir,
    # mas as variáveis de ambiente passadas pelo Docker Compose terão precedência.
    load_dotenv(dotenv_path=Settings().Config.env_file)
    return Settings()

settings = get_settings()
