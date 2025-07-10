from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "PolicyEngineService"
    API_V1_STR: str = "/api/v1"

    class Config:
        case_sensitive = True
        # env_file = ".env"
        # env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
