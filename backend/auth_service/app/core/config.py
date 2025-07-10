from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "AuthService"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = (
        "postgresql://user:password@localhost:5432/authdb_mvp"  # Exemplo, idealmente de .env
    )

    # JWT
    JWT_SECRET_KEY: str = "super-secret-key"  # Mudar isso e carregar de .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia

    # Google OAuth
    GOOGLE_CLIENT_ID: str = "YOUR_GOOGLE_CLIENT_ID"  # Carregar de .env
    GOOGLE_CLIENT_SECRET: str = "YOUR_GOOGLE_CLIENT_SECRET"  # Carregar de .env
    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/google/callback"  # Ajustar conforme necessário
    )

    class Config:
        case_sensitive = True
        # Para carregar de um arquivo .env em desenvolvimento:
        # env_file = ".env"
        # env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
