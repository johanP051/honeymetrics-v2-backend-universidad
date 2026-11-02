from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_names: str
    last_names: str
    role_id: int
    role_name: Optional[str] = None
    is_active: bool
    must_change_password: bool
    scopes: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: Optional[UserResponse] = None
    mfa_required: bool = False
    must_change_password: bool = False
    scopes: List[str] = []


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MfaSetupResponse(BaseModel):
    secret: str
    qr: str


class MfaVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="Código TOTP de 6 dígitos")


class MfaVerifyResponse(BaseModel):
    message: str
    backup_codes: List[str] = []
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MfaDisableResponse(BaseModel):
    message: str
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MfaVerifyLoginRequest(BaseModel):
    mfa_token: str
    code: Optional[str] = Field(
        default=None,
        description="Código TOTP (6 dígitos) o código de respaldo (XXXX-XXXX)",
    )
    totp_code: Optional[str] = Field(
        default=None,
        description="Alias de código TOTP compatible con frontend y versiones previas",
    )

    @model_validator(mode="after")
    def validate_code_presence_and_format(self) -> "MfaVerifyLoginRequest":
        effective_code = self.code or self.totp_code
        if not effective_code:
            raise ValueError("El código de verificación ('code' o 'totp_code') es obligatorio.")
        clean = effective_code.strip()
        if len(clean) not in (6, 8, 9):
            raise ValueError("El código debe contener 6 dígitos (TOTP) o formato de respaldo (XXXX-XXXX).")
        self.code = clean
        return self


class MfaTokenResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str