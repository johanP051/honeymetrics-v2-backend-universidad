import time
from datetime import datetime, timezone
from app.core.config import settings
from app.schemas.health import HealthResponseDto

# Registro del momento en que se inicializa el servicio
_SERVER_START_TIME = time.time()


class HealthService:
    """
    Capa de Servicio para la comprobación de salud del sistema.
    Aísla la lógica de cálculo de uptime y telemetría de los controladores HTTP.
    """

    @classmethod
    def get_health_status(cls) -> HealthResponseDto:
        """
        Calcula el tiempo de actividad y genera el DTO con el estado general.
        """
        uptime = round(time.time() - _SERVER_START_TIME, 2)
        current_time = datetime.now(timezone.utc)

        return HealthResponseDto(
            status="online",
            service=settings.PROJECT_NAME,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            uptime_seconds=uptime,
            timestamp=current_time,
        )
