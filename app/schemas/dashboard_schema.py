"""
Esquemas Pydantic para el Reporte Ejecutivo del Dashboard.
HoneyMetrics Backend v2.0 (UDEC)
"""
from typing import List
from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_threats_tracked: int = Field(ge=0)
    active_blocks: int = Field(ge=0)
    registered_users: int = Field(ge=0)
    total_forensic_exports: int = Field(ge=0)
    average_threat_score: float = Field(ge=0)


class DashboardCountryMetric(BaseModel):
    country: str
    count: int = Field(ge=0)


class DashboardThreatMetric(BaseModel):
    ip: str
    score: int = Field(ge=0, le=100)
    category: str
    status: str


class DashboardThreatLandscape(BaseModel):
    top_countries: List[DashboardCountryMetric]
    top_threats: List[DashboardThreatMetric]


class ExecutiveDashboardReport(BaseModel):
    summary: DashboardSummary
    threat_landscape: DashboardThreatLandscape
