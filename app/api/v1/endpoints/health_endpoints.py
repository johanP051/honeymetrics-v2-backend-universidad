"""
Endpoint de Health Check de la API.
HoneyMetrics Backend v2.0 (UDEC)
"""
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.threat_schema import HealthResponseSchema

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponseSchema, summary="Verificar estado de la API")
async def health_check() -> HealthResponseSchema:
    """Retorna 200 OK con el estado de salud general del servicio HoneyMetrics API."""
    return HealthResponseSchema(
        status="healthy",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
    )
