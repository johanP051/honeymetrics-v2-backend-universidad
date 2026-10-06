from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import ipaddress


class BlacklistEntryCreate(BaseModel):
    """DTO de entrada para registrar una nueva IP en la Blacklist."""

    ip: str = Field(..., description="Dirección IP del atacante o IOC", example="45.148.10.151")
    ip_type: str = Field(default="IPv4", description="Tipo de indicador (IPv4, IPv6)")
    country: str = Field(default="Unknown", description="País de origen estimado")
    threat_score: int = Field(..., ge=0, le=100, description="Puntuación de amenaza (0 a 100)")
    category: str = Field(..., description="Categoría: APT, Botnet, Scanner, Recon")
    notes: Optional[str] = Field(default=None, description="Anotaciones técnicas del SOC")

    @field_validator("ip")
    @classmethod
    def validate_ip_format(cls, v: str) -> str:
        """Valida que el campo sea una dirección IP sintácticamente correcta."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"'{v}' no es una dirección IP válida.")
        return v


class BlacklistEntryUpdate(BaseModel):
    """DTO de actualización parcial (PATCH-style) para una entrada de Blacklist."""

    ip: Optional[str] = Field(default=None)
    ip_type: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    threat_score: Optional[int] = Field(default=None, ge=0, le=100)
    category: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None, description="Override manual: Bloqueada | Monitoreada")
    notes: Optional[str] = Field(default=None)

    @field_validator("ip")
    @classmethod
    def validate_ip_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"'{v}' no es una dirección IP válida.")
        return v


class BlacklistEntryResponse(BaseModel):
    """DTO de salida con datos completos de una entrada en la Blacklist."""

    id: int
    ip: str
    ip_type: str
    country: str
    threat_score: int
    category: str
    status: str
    notes: Optional[str]
    blocked_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
