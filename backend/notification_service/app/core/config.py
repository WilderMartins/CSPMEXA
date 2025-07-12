from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "NotificationService"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    RELOAD_UVICORN: bool = False
    NOTIFICATION_SERVICE_PORT: int = 8003
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Service for handling notifications."

    # Email Settings
    DEFAULT_CRITICAL_ALERT_RECIPIENT_EMAIL: Optional[str] = None
    AWS_REGION: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = "CSPMEXA Platform"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    # Webhook Settings
    WEBHOOK_DEFAULT_URL: Optional[str] = None

    # Google Chat Settings
    GOOGLE_CHAT_WEBHOOK_URL: Optional[str] = None

    # Internal API Key
    INTERNAL_API_KEY: str = "change-this-in-production"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
