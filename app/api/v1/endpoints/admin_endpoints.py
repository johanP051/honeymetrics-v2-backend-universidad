"""
Endpoints del Panel de Administración — Gestión de Usuarios del sistema.
Todos los endpoints requieren rol Administrador.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.db.session import get_db
from app.models.user_model import User
from app.services.admin_service import (
    AdminService,
    UserListItemResponse,
    UserCreateAdminRequest,
    UserUpdateAdminRequest,
)

router = APIRouter(
    prefix="/admin",
    tags=["Panel de Administración"],
)


@router.get(
    "/users",
    response_model=List[UserListItemResponse],
    summary="Listar usuarios del sistema con filtros [ADMIN]",
)
def list_users(
    search: Optional[str] = Query(default=None, description="Búsqueda por email"),
    role_id: Optional[int] = Query(default=None, description="Filtrar por ID de rol"),
    is_active: Optional[bool] = Query(default=None, description="Filtrar por estado activo/inactivo"),
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> List[UserListItemResponse]:
    """
    Retorna todos los usuarios del sistema con soporte de filtros combinados.
    Requiere rol Administrador.
    """
    return AdminService.list_users(db, search=search, role_id=role_id, is_active=is_active)


@router.post(
    "/users",
    response_model=UserListItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario con contraseña temporal [ADMIN]",
)
def create_user(
    payload: UserCreateAdminRequest,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    """
    Crea una nueva cuenta de usuario con contraseña temporal.
    El usuario deberá cambiarla en su primer inicio de sesión.
    Requiere rol Administrador.
    """
    return AdminService.create_user(payload, db)


@router.put(
    "/users/{user_id}",
    response_model=UserListItemResponse,
    summary="Modificar rol o estado de un usuario [ADMIN]",
)
def update_user(
    user_id: int,
    payload: UserUpdateAdminRequest,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    """
    Actualiza el rol o estado activo/inactivo de un usuario.
    Un administrador no puede desactivar su propia cuenta.
    Requiere rol Administrador.
    """
    return AdminService.update_user(user_id, payload, current_admin_id=current_admin.id, db=db)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario del sistema [ADMIN]",
)
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Elimina permanentemente un usuario del sistema.
    Un administrador no puede eliminarse a sí mismo.
    Requiere rol Administrador.
    """
    AdminService.delete_user(user_id, current_admin_id=current_admin.id, db=db)
    return {"message": f"Usuario ID {user_id} eliminado exitosamente del sistema."}
