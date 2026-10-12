"""
Endpoints de Gestión de Roles del Sistema.
Permite consultar, registrar y eliminar roles con control de acceso basado en permisos (PBAC).
"""
from typing import List
from fastapi import APIRouter, Security, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.role_schema import RoleItemResponse, RoleCreateRequest
from app.services.role_service import RoleService

router = APIRouter()


@router.get(
    "",
    response_model=List[RoleItemResponse],
    summary="Consultar lista de roles con conteo de usuarios asociados",
)
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RoleItemResponse]:
    """Retorna todos los roles del sistema junto con la cantidad de usuarios asignados."""
    return RoleService.list_roles_with_counts(db)


@router.post(
    "",
    response_model=RoleItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo Rol en el sistema [ADMIN]",
)
def create_role(
    payload: RoleCreateRequest,
    current_admin: User = Security(get_current_user, scopes=["admin:all"]),
    db: Session = Depends(get_db),
) -> RoleItemResponse:
    """Crea un nuevo rol asegurando unicidad en el nombre. Requiere scope 'admin:all'."""
    return RoleService.create_role(payload, db)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un rol del sistema si no tiene usuarios asignados [ADMIN]",
)
def delete_role(
    role_id: int,
    current_admin: User = Security(get_current_user, scopes=["admin:all"]),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina un rol existente si no es Administrador y no tiene usuarios asignados."""
    RoleService.delete_role(role_id, db)
    return {"message": "Rol eliminado exitosamente."}
