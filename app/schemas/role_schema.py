from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RoleItemResponse(BaseModel):
    id: int = Field(..., description="Identificador único del rol")
    name: str = Field(..., description="Nombre canónico o asignado del rol")
    description: Optional[str] = Field(None, description="Descripción de las responsabilidades del rol")
    user_count: int = Field(default=0, description="Cantidad de usuarios asociados a este rol")

    model_config = ConfigDict(from_attributes=True)


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Nombre único del rol")
    description: Optional[str] = Field(None, max_length=255, description="Descripción de las responsabilidades del rol")
