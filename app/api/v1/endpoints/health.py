from fastapi import APIRouter, status
from app.schemas.health import HealthResponseDto
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponseDto,
    status_code=status.HTTP_200_OK,
    summary="Verificar salud y telemetría de la API",
    description="Controlador liviano que delega el cálculo de estado y uptime al HealthService.",
)
async def get_health() -> HealthResponseDto:
    """Retorna el diagnóstico operacional del sistema."""
    return HealthService.get_health_status()
