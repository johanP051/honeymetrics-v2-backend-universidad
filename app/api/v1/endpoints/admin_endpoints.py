"""
Endpoints del Panel de Administración — Gestión de Usuarios y Auditoría.
Todos los endpoints requieren rol Administrador.
"""
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.admin_schema import (
    AuditLogResponse,
    UserCreateAdminRequest,
    UserListItemResponse,
    UserUpdateAdminRequest,
)
from app.services.admin_service import AdminService
from app.services.email_service import EmailService

router = APIRouter(
    prefix="/admin",
    tags=["Panel de Administración"],
)
admin_users_router = APIRouter(
    prefix="/users",
    tags=["Gestión de Usuarios (Admin)"],
)


@router.get(
    "/users",
    response_model=List[UserListItemResponse],
    summary="Listar usuarios del sistema con filtros [ADMIN]",
)
@admin_users_router.get(
    "",
    include_in_schema=False,
    response_model=List[UserListItemResponse],
)
@admin_users_router.get(
    "/",
    response_model=List[UserListItemResponse],
    summary="Listar usuarios del sistema con filtros [ADMIN] (alias /users)",
)
def list_users(
    search: Optional[str] = Query(default=None, description="Búsqueda por email"),
    role_id: Optional[int] = Query(default=None, description="Filtrar por ID de rol"),
    is_active: Optional[bool] = Query(default=None, description="Filtrar por estado activo/inactivo"),
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> List[UserListItemResponse]:
    """Retorna todos los usuarios del sistema con soporte de filtros combinados."""
    return AdminService.list_users(db, search=search, role_id=role_id, is_active=is_active)


@router.post(
    "/users",
    response_model=UserListItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario con contraseña temporal [ADMIN]",
)
@admin_users_router.post(
    "",
    include_in_schema=False,
    response_model=UserListItemResponse,
    status_code=status.HTTP_201_CREATED,
)
@admin_users_router.post(
    "/",
    response_model=UserListItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario con contraseña temporal [ADMIN] (alias /users)",
)
def create_user(
    payload: UserCreateAdminRequest,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    """Crea una nueva cuenta de usuario con contraseña temporal."""
    created_user = AdminService.create_user(payload, db)
    if payload.send_email:
        background_tasks.add_task(
            EmailService.send_welcome_email,
            email=str(payload.email),
            temp_password=payload.temp_password,
        )
    return created_user


@router.put(
    "/users/{user_id}",
    response_model=UserListItemResponse,
    summary="Modificar rol o estado de un usuario [ADMIN]",
)
@admin_users_router.put(
    "/{user_id}",
    response_model=UserListItemResponse,
    summary="Modificar rol o estado de un usuario [ADMIN] (alias /users)",
)
def update_user(
    user_id: int,
    payload: UserUpdateAdminRequest,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    """Actualiza el rol o estado activo/inactivo de un usuario."""
    return AdminService.update_user(user_id, payload, current_admin_id=current_admin.id, db=db)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario del sistema [ADMIN]",
)
@admin_users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario del sistema [ADMIN] (alias /users)",
)
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina permanentemente un usuario del sistema resolviendo FKs."""
    AdminService.delete_user(user_id, current_admin_id=current_admin.id, db=db)
    return {"message": f"Usuario ID {user_id} eliminado exitosamente del sistema."}


@router.post(
    "/users/{user_id}/mfa/reset",
    summary="Resetear autenticación 2FA de un usuario [ADMIN]",
)
@admin_users_router.post(
    "/{user_id}/mfa/reset",
    summary="Resetear autenticación 2FA de un usuario [ADMIN] (alias /users)",
)
def reset_user_mfa(
    user_id: int,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    """Resetea MFA y códigos de respaldo para contingencia administrativa."""
    return AdminService.reset_user_mfa(user_id, current_admin_id=current_admin.id, db=db)


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Consultar registros de la tabla de auditoría [ADMIN]",
)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500, description="Límite de registros"),
    offset: int = Query(default=0, ge=0, description="Desplazamiento inicial"),
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> List[AuditLogResponse]:
    """Retorna los registros de auditoría ordenados descendentemente por fecha."""
    return AdminService.list_audit_logs(db=db, limit=limit, offset=offset)
