"""
Esquemas DTOs para el Panel de Administración y Auditoría.
HoneyMetrics Backend v2.0 (UDEC)
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_policy import validate_new_password


class UserListItemResponse(BaseModel):
    id: int
    email: str
    first_names: str
    last_names: str
    role_name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateAdminRequest(BaseModel):
    email: EmailStr
    first_names: str = Field(..., min_length=2)
    last_names: str = Field(..., min_length=2)
    role_id: int = Field(..., description="ID del rol a asignar")
    temp_password: str = Field(
        ..., min_length=12, max_length=128,
        description="Contraseña temporal (política ASVS V2.1: 12-128 caracteres + denylist)",
    )
    send_email: bool = Field(default=True, description="Enviar correo de bienvenida")

    @field_validator("temp_password")
    @classmethod
    def validate_temp_password_policy(cls, v: str) -> str:
        """OWASP ASVS 4.0.3 V2.1: 12-128 caracteres, denylist y sin composición forzada."""
        return validate_new_password(v)


class UserUpdateAdminRequest(BaseModel):
    role_id: Optional[int] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    entity_name: str
    entity_id: Optional[str] = None
    details: Optional[Any] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
