import secrets
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HoneyMetrics v2 API (UDEC)"
    VERSION: str = "2.0.0-academic"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas para estabilidad de sesión SOC
    REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN: bool = True

    # Frontend Config & CORS
    FRONTEND_URL: str = "http://localhost:5174"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
        "https://honeymetrics-v2-frontend.johan-sebastianposada.workers.dev",
        "https://honeymetrics-frontend.johan-sebastianposada.workers.dev",
    ]

    # Correo transaccional Resend (PB-HM-06.1, ente UDEC distinto de guía)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "HoneyMetrics UDEC <udec-auth@johan-d3v.site>"

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

    # Wazuh Indexer (OpenSearch SIEM)
    WAZUH_INDEXER_URL: str = ""
    WAZUH_INDEXER_USER: str = ""
    WAZUH_INDEXER_PASSWORD: str = ""
    WAZUH_TLS_VERIFY: bool = True

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        if self.ENVIRONMENT in {"staging", "production"}:
            required = {
                "SECRET_KEY": self.SECRET_KEY,
                "WAZUH_INDEXER_URL": self.WAZUH_INDEXER_URL,
                "WAZUH_INDEXER_USER": self.WAZUH_INDEXER_USER,
                "WAZUH_INDEXER_PASSWORD": self.WAZUH_INDEXER_PASSWORD,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(
                    "Configuración insegura: faltan variables requeridas: "
                    + ", ".join(missing)
                )
        elif not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_urlsafe(32)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
