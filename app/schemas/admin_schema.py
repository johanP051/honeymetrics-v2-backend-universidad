"""
Esquemas DTOs para el Panel de Administración y Auditoría.
HoneyMetrics Backend v2.0 (UDEC)
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    temp_password: str = Field(..., min_length=8, description="Contraseña temporal")
    send_email: bool = Field(default=True, description="Enviar correo de bienvenida")


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
