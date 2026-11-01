"""
Esquemas DTOs para Perfil de Usuario y Cambio de Contraseña.
HoneyMetrics Backend v2.0 (UDEC) - OWASP ASVS V2.1 / API3:2023.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.core.password_policy import validate_new_password


class UserProfileResponse(BaseModel):
    """DTO de salida para GET /api/v1/users/me y PUT /api/v1/users/me."""
    id: int
    email: EmailStr
    first_names: str
    last_names: str
    role_id: int
    role_name: str
    is_active: bool
    is_mfa_enabled: bool
    must_change_password: bool
    scopes: list[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    """
    DTO de entrada para PUT /api/v1/users/me.
    BLINDAJE ANTI-MASS ASSIGNMENT (OWASP API3:2023):
    Usa extra='forbid' y únicamente admite campos de identidad personal.
    Cualquier intento de inyectar role_id, is_active, is_mfa_enabled,
    hashed_password o auth_version será rechazado automáticamente con HTTP 422.
    """
    model_config = ConfigDict(extra="forbid")

    first_names: Optional[str] = Field(
        default=None, min_length=2, max_length=150, description="Nombres del usuario"
    )
    last_names: Optional[str] = Field(
        default=None, min_length=2, max_length=150, description="Apellidos del usuario"
    )
    email: Optional[EmailStr] = Field(
        default=None, description="Correo electrónico (sujeto a validación de unicidad)"
    )

    @field_validator("first_names", "last_names")
    @classmethod
    def strip_and_validate_names(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = " ".join(v.strip().split())
            if len(cleaned) < 2:
                raise ValueError("El campo debe contener al menos 2 caracteres válidos.")
            return cleaned
        return v


class PasswordChangeRequest(BaseModel):
    """DTO para cambio voluntario u obligatorio de contraseña en PUT /api/v1/users/me/password."""
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(..., min_length=1, description="Contraseña actual")
    new_password: str = Field(..., min_length=12, max_length=128, description="Nueva contraseña (ASVS V2.1)")
    confirm_password: str = Field(..., min_length=12, max_length=128, description="Confirmación de nueva contraseña")

    @field_validator("new_password")
    @classmethod
    def validate_strength(cls, v: str, info) -> str:
        current_pwd = info.data.get("current_password")
        return validate_new_password(v, current_password=current_pwd)

    @field_validator("confirm_password")
    @classmethod
    def passwords_must_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Las contraseñas no coinciden.")
        return v
