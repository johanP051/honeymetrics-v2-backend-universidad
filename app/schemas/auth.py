from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequestDto(BaseModel):
    """DTO para la solicitud de inicio de sesión."""
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    password: str = Field(..., min_length=6, description="Contraseña en texto plano")


class TokenResponseDto(BaseModel):
    """DTO para la entrega del token de acceso JWT."""
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class UserResponseDto(BaseModel):
    """DTO para responder información de usuario sin filtrar datos sensibles."""
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
