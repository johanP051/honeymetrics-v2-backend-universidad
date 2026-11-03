from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AttackerIPSchema(BaseModel):
    """Esquema de representación de una IP atacante identificada por telemetría CTI."""

    ip: str = Field(..., description="Dirección IP del atacante")
    country: str = Field(default="Unknown", description="País de origen del atacante")
    total_events: int = Field(..., examples=[46026], description="Total de intentos/eventos registrados")
    threat_score: int = Field(..., ge=0, le=100, examples=[93], description="Puntuación de amenaza (0 a 100)")
    badge: str = Field(
        ...,
        examples=["APT"],
        description="Categoría de amenaza (APT, Botnet Storm, Recon, Scanner)",
    )
    primary_tactic: str = Field(
        ...,
        examples=["Credential Access"],
        description="Táctica MITRE ATT&CK predominante",
    )
    targeted_users: List[str] = Field(
        default_factory=list,
        examples=[["root", "admin"]],
        description="Usuarios vulnerados o intentados",
    )
    is_persistent: bool = Field(default=False, description="Indica si la IP atacó en múltiples meses")
    months_active: List[str] = Field(
        default_factory=list,
        examples=[["2026-04", "2026-06", "2026-07"]],
        description="Meses con actividad registrada",
    )
    avg_severity: float = Field(..., examples=[5.5], description="Severidad promedio de eventos Wazuh")


class BotnetSubnetSchema(BaseModel):
    """Esquema de subred sospechosa de operar como botnet coordinada."""

    subnet: str = Field(..., description="Subred CIDR identificada")
    total_events: int = Field(..., examples=[5613], description="Total de eventos originados en el prefijo")
    distinct_ips_count: int = Field(..., examples=[7], description="Cantidad de nodos atacantes únicos")
    sample_ips: List[str] = Field(default_factory=list, description="Muestra representativa de IPs atacantes")
    suggested_action: str = Field(default="Request analyst review", description="Acción de mitigación sugerida")


class ThreatSummarySchema(BaseModel):
    """Resumen consolidado de métricas e indicadores para el Dashboard principal."""

    total_analyzed_events: int = Field(..., examples=[165247], description="Volumen total de eventos analizados")
    unique_attacker_ips: int = Field(..., examples=[1107], description="Cantidad total de atacantes únicos")
    persistent_threats_count: int = Field(
        ..., examples=[9], description="Cantidad de amenazas persistentes identificadas"
    )
    active_critical_cves_count: int = Field(..., examples=[1721], description="Total de CVEs críticos observados")
    peak_hour_utc: str = Field(
        ...,
        examples=["11:00 - 12:00 UTC"],
        description="Franja horaria pico de incidentes (UTC)",
    )
    top_attackers: List[AttackerIPSchema] = Field(default_factory=list, description="Top de atacantes por Threat Score")
    detected_botnets: List[BotnetSubnetSchema] = Field(default_factory=list, description="Botnets detectadas por CIDR")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp de generación",
    )


class HealthResponseSchema(BaseModel):
    """Esquema para health check del motor y servicio CTI."""

    status: str = Field(default="healthy", description="Estado del servicio")
    service: str = Field(default="HoneyMetrics v2 API (UDEC)", description="Nombre del servicio")
    environment: str = Field(..., description="Entorno de despliegue")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp UTC")


class BlacklistVaultResponse(BaseModel):
    """DTO de salida para la Bóveda Forense de Lista Negra."""

    id: int = Field(..., description="ID del registro archivado en la bóveda")
    original_entry_id: int = Field(..., description="ID original en blacklist_entries")
    original_ip: str = Field(..., description="Dirección IP del atacante")
    ip_type: Optional[str] = Field(default="IPv4", description="Protocolo (IPv4 o IPv6)")
    country: Optional[str] = Field(default="Unknown", description="País de procedencia")
    threat_score: int = Field(..., ge=0, le=100, description="Puntuación de amenaza")
    category: Optional[str] = Field(default=None, description="Categoría de amenaza")
    status: Optional[str] = Field(default=None, description="Estado al momento de eliminación")
    notes: Optional[str] = Field(default=None, description="Notas forenses")
    deleted_by_user_id: Optional[int] = Field(default=None, description="ID del usuario que eliminó la entrada")
    deleted_at: datetime = Field(..., description="Timestamp UTC de eliminación")
    full_record_json: Optional[Dict[str, Any]] = Field(default=None, description="Snapshot serializado completo")

    model_config = ConfigDict(from_attributes=True)
