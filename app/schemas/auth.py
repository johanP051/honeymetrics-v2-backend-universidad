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
    is_active: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse | None = None
# Literal["bearer"] significa que el campo solo puede ser bearer; = "bearer" le asigna un valor por defecto si el cliente no envia token_type