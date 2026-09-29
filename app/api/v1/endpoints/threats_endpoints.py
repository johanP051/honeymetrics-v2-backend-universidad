from datetime import date
from typing import List, Optional, Literal
from fastapi import APIRouter, Query
from app.core.config import settings
from app.schemas.threat_schema import (
    AttackerIPSchema,
    BotnetSubnetSchema,
    ThreatSummarySchema,
    HealthResponseSchema,
)
from app.services.threat_service import ThreatService

router = APIRouter(prefix="/threats", tags=["Threat Intelligence"])


@router.get("/summary", response_model=ThreatSummarySchema, summary="Resumen global de CTI con filtrado temporal")
async def get_threat_summary(
    range: Optional[Literal["24h", "7d", "30d", "90d"]] = Query(None, description="Preset temporal: 24h, 7d, 30d, 90d"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
) -> ThreatSummarySchema:
    """Retorna las métricas consolidadas de amenazas con filtrado temporal."""
    return await ThreatService.get_threat_summary(
        range_preset=range,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/top-persistent", response_model=List[AttackerIPSchema], summary="Top Amenazas Persistentes")
async def get_top_persistent() -> List[AttackerIPSchema]:
    """Retorna las IPs atacantes con mayor persistencia y Threat Score."""
    return await ThreatService.get_top_persistent_threats()


@router.get("/botnets", response_model=List[BotnetSubnetSchema], summary="Botnets detectadas por CIDR")
async def get_detected_botnets() -> List[BotnetSubnetSchema]:
    """Retorna los grupos de IPs atacantes coordinadas por subred /24."""
    return await ThreatService.get_detected_botnets()


@router.get("/health", response_model=HealthResponseSchema, summary="Verificar estado del motor CTI")
async def health_check() -> HealthResponseSchema:
    """Retorna el estado de salud del servicio de Threat Intelligence."""
    from app.services.wazuh_extractor import WazuhExtractor
    is_online = await WazuhExtractor.check_connection()
    status_val = "healthy" if is_online else "degraded"
    
    return HealthResponseSchema(
        status=status_val,
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
    )
