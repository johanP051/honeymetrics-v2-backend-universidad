"""
AdminService — Gestión de usuarios desde el panel de administración.

Invariantes de Dominio:
  1. Un administrador no puede eliminar su propia cuenta (auto-eliminación).
  2. Un administrador no puede desactivar su propia cuenta.
  3. La contraseña se hashea con Argon2 antes de persistir.
"""
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user_model import User
from app.models.role_model import Role


# ─── DTOs internos del Admin Service ────────────────────────────────────────

class UserListItemResponse(BaseModel):
    id: int
    email: str
    first_names: str
    last_names: str
    role_name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateAdminRequest(BaseModel):
    email: EmailStr
    first_names: str = Field(..., min_length=2)
    last_names: str = Field(..., min_length=2)
    role_id: int = Field(..., description="ID del rol a asignar")
    temp_password: str = Field(..., min_length=8, description="Contraseña temporal (el usuario debe cambiarla)")


class UserUpdateAdminRequest(BaseModel):
    role_id: Optional[int] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


# ─── Service ────────────────────────────────────────────────────────────────

class AdminService:
    """
    Lógica de negocio para el panel de administración de usuarios.
    Todos los métodos validan que los roles existan en la BD antes de asignarlos.
    """

    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List[UserListItemResponse]:
        """Lista usuarios con filtros opcionales de búsqueda, rol y estado."""
        query = db.query(User)

        if search:
            query = query.filter(User.email.ilike(f"%{search}%"))
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        users = query.order_by(User.created_at.desc()).all()

        return [
            UserListItemResponse(
                id=u.id,
                email=u.email,
                first_names=u.first_names,
                last_names=u.last_names,
                role_name=u.role.name if u.role else "Sin Rol",
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]

    @staticmethod
    def create_user(payload: UserCreateAdminRequest, db: Session) -> UserListItemResponse:
        """
        Crea un nuevo usuario con contraseña temporal.
        Valida que el email no esté duplicado y que el rol exista.
        """
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un usuario registrado con el correo '{payload.email}'.",
            )

        role = db.query(Role).filter(Role.id == payload.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El rol con ID {payload.role_id} no existe en el sistema.",
            )

        user = User(
            email=str(payload.email),
            first_names=payload.first_names,
            last_names=payload.last_names,
            hashed_password=hash_password(payload.temp_password),
            role_id=payload.role_id,
            is_active=True,
            must_change_password=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return UserListItemResponse(
            id=user.id,
            email=user.email,
            first_names=user.first_names,
            last_names=user.last_names,
            role_name=role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    @staticmethod
    def update_user(
        user_id: int,
        payload: UserUpdateAdminRequest,
        current_admin_id: int,
        db: Session,
    ) -> UserListItemResponse:
        """
        Actualiza rol o estado activo de un usuario.
        Guarda: un admin no puede desactivar su propia cuenta.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado.",
            )

        if payload.is_active is False and user.id == current_admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrador no puede desactivar su propia cuenta.",
            )

        if payload.role_id is not None:
            role = db.query(Role).filter(Role.id == payload.role_id).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El rol con ID {payload.role_id} no existe.",
                )
            user.role_id = payload.role_id

        if payload.is_active is not None:
            user.is_active = payload.is_active

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        return UserListItemResponse(
            id=user.id,
            email=user.email,
            first_names=user.first_names,
            last_names=user.last_names,
            role_name=user.role.name if user.role else "Sin Rol",
            is_active=user.is_active,
            created_at=user.created_at,
        )

    @staticmethod
    def delete_user(user_id: int, current_admin_id: int, db: Session) -> None:
        """
        Elimina un usuario permanentemente.
        Guarda: un admin no puede eliminarse a sí mismo.
        """
        if user_id == current_admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrador no puede eliminar su propia cuenta.",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado.",
            )

        db.delete(user)
        db.commit()
