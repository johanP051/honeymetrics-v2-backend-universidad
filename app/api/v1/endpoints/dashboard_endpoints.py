"""
Endpoints de Dashboard y Reportes Ejecutivos.
HoneyMetrics Backend v2.0 (UDEC)
"""
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.dashboard_schema import ExecutiveDashboardReport
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/report/executive",
    response_model=ExecutiveDashboardReport,
    summary="Obtener el reporte ejecutivo del Dashboard",
)
def get_executive_report(
    db: Session = Depends(get_db),
    _current_user: User = Security(get_current_user, scopes=["dashboard:read"]),
) -> dict:
    """
    Consolida las métricas globales para el rol Directivo de T.I. y Administrador.
    Sirve como fuente estructurada para la generación de reportes empresariales.
    """
    return DashboardService.get_executive_report(db)
