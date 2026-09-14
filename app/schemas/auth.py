from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_names: str
    last_names: str
    role_id: int
    is_active: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)