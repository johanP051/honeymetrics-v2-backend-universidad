from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HoneyMetrics v2 API (UDEC)"
    VERSION: str = "2.0.0-academic"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "supersecretkey_change_in_production_generate_with_openssl"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN: bool = True

    # Frontend Config & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database: Por defecto SQLite para desarrollo inmediato sin dependencias duras;
    # se sobrescribe con PostgreSQL mediante DATABASE_URL en .env o Docker.
    DATABASE_URL: str = "sqlite:///./honeymetrics_v2.db"

    # Cloudflare Zero Trust (Opcional)
    CLOUDFLARE_TUNNEL_TOKEN: str = ""

    # Telegram Bot & Webhooks (Human-in-the-loop para aprobaciones)
    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
