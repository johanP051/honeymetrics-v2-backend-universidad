from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class HealthResponseDto(BaseModel):
    """
    DTO de Respuesta para el diagnóstico del sistema.
    Cumple el patrón Data Transfer Object aislando detalles internos del servidor.
    """
    status: str = Field(..., description="Estado operativo del servicio (online / degraded / offline)")
    service: str = Field(..., description="Nombre del servicio o microservicio")
    version: str = Field(..., description="Versión semántica del backend")
    environment: str = Field(..., description="Entorno de ejecución (development / staging / production)")
    uptime_seconds: float = Field(..., description="Segundos transcurridos desde el inicio del servidor")
    timestamp: datetime = Field(..., description="Marca de tiempo en formato ISO-8601 UTC")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "online",
                "service": "HoneyMetrics v2 API (UDEC)",
                "version": "2.0.0-academic",
                "environment": "development",
                "uptime_seconds": 45.2,
                "timestamp": "2026-09-10T14:40:00Z"
            }
        }
    )
