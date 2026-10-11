from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Literal es una caracteristica de pydantic que restringe los valores posibles a solo los especificados

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_names: str
    last_names: str
    role_id: int
    role_name: str | None = None
    is_active: bool
    must_change_password: bool
    scopes: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse | None = None
    mfa_required: bool = False
    scopes: list[str] = []


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MfaSetupResponse(BaseModel):
    secret: str
    qr: str


class MfaVerifyRequest(BaseModel):
    code: str


class MfaVerifyLoginRequest(BaseModel):
    mfa_token: str
    code: str


class MfaTokenResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str
# Literal["bearer"] significa que el campo solo puede ser bearer; = "bearer" le asigna un valor por defecto si el cliente no envia token_type