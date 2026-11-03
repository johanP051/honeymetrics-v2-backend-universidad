"""
AdminService — Gestión de usuarios y contingencia administrativa.
HoneyMetrics Backend v2.0 (UDEC)
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.audit_log_model import AuditLog
from app.models.blacklist_model import BlacklistEntry
from app.models.blacklist_vault_model import BlacklistAuditVault
from app.models.mfa_backup_code_model import MFABackupCode
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.admin_schema import (
    AuditLogResponse,
    UserCreateAdminRequest,
    UserListItemResponse,
    UserUpdateAdminRequest,
)
from app.services.audit_service import AuditService
from app.services.email_service import EmailService

__all__ = [
    "AdminService",
    "UserListItemResponse",
    "UserCreateAdminRequest",
    "UserUpdateAdminRequest",
    "AuditLogResponse",
]


class AdminService:
    @staticmethod
    def _to_dto(user: User, role_name: Optional[str] = None) -> UserListItemResponse:
        return UserListItemResponse(
            id=user.id,
            email=user.email,
            first_names=user.first_names,
            last_names=user.last_names,
            role_name=role_name or (user.role.name if user.role else "Sin Rol"),
            is_active=user.is_active,
            created_at=user.created_at,
        )

    @classmethod
    def list_users(
        cls, db: Session, search: Optional[str] = None,
        role_id: Optional[int] = None, is_active: Optional[bool] = None
    ) -> List[UserListItemResponse]:
        query = db.query(User)
        if search:
            query = query.filter(User.email.ilike(f"%{search}%"))
        if role_id is not None:
            query = query.filter(User.role_id == role_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        return [cls._to_dto(u) for u in query.order_by(User.created_at.desc()).all()]

    @classmethod
    def create_user(cls, payload: UserCreateAdminRequest, db: Session) -> UserListItemResponse:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un usuario con el correo '{payload.email}'.")
        role = db.query(Role).filter(Role.id == payload.role_id).first()
        if not role:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"El rol con ID {payload.role_id} no existe.")

        now = datetime.now(timezone.utc)
        user = User(
            email=str(payload.email), first_names=payload.first_names, last_names=payload.last_names,
            hashed_password=hash_password(payload.temp_password), role_id=payload.role_id,
            is_active=True, must_change_password=True, created_at=now, updated_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return cls._to_dto(user, role_name=role.name)

    @classmethod
    def update_user(
        cls, user_id: int, payload: UserUpdateAdminRequest, current_admin_id: int, db: Session
    ) -> UserListItemResponse:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Usuario con ID {user_id} no encontrado.")

        if user.id == current_admin_id:
            if payload.is_active is False:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un administrador no puede desactivar su propia cuenta.")
            if payload.role_id is not None and payload.role_id != user.role_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un administrador no puede modificar o degradar su propio rol.")

        changed = False
        if payload.first_names is not None and payload.first_names.strip():
            user.first_names = payload.first_names.strip()
            changed = True
        if payload.last_names is not None and payload.last_names.strip():
            user.last_names = payload.last_names.strip()
            changed = True
        if payload.email is not None and str(payload.email).strip():
            new_email = str(payload.email).strip().lower()
            if new_email != user.email:
                existing = db.query(User).filter(User.email == new_email).first()
                if existing and existing.id != user.id:
                    raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un usuario con el correo '{new_email}'.")
                user.email = new_email
                changed = True
        if payload.role_id is not None and payload.role_id != user.role_id:
            if not db.query(Role).filter(Role.id == payload.role_id).first():
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"El rol con ID {payload.role_id} no existe.")
            user.role_id = payload.role_id
            changed = True
        if payload.is_active is not None and payload.is_active != user.is_active:
            user.is_active = payload.is_active
            changed = True
        if payload.password is not None and payload.password.strip():
            user.hashed_password = hash_password(payload.password.strip())
            user.must_change_password = True
            changed = True

        if changed:
            user.auth_version = int(getattr(user, "auth_version", 0) or 0) + 1

        admin = db.query(User).filter(User.id == current_admin_id).first()
        AuditService.log_event(
            db, action="ADMIN_USER_UPDATED", entity_name="users", actor_user_id=current_admin_id,
            actor_email=admin.email if admin else None, entity_id=str(user_id),
            details={
                "role_id": user.role_id,
                "is_active": user.is_active,
                "password_updated": bool(payload.password and payload.password.strip()),
            },
        )
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return cls._to_dto(user)

    @staticmethod
    def delete_user(user_id: int, current_admin_id: int, db: Session) -> None:
        if user_id == current_admin_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Un administrador no puede eliminar su propia cuenta.")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Usuario con ID {user_id} no encontrado.")

        db.query(MFABackupCode).filter(MFABackupCode.user_id == user_id).delete(synchronize_session=False)
        db.query(BlacklistEntry).filter(BlacklistEntry.blocked_by_user_id == user_id).update(
            {BlacklistEntry.blocked_by_user_id: None}, synchronize_session=False
        )
        db.query(BlacklistAuditVault).filter(BlacklistAuditVault.deleted_by_user_id == user_id).update(
            {BlacklistAuditVault.deleted_by_user_id: None}, synchronize_session=False
        )
        db.query(AuditLog).filter(AuditLog.actor_user_id == user_id).update(
            {AuditLog.actor_user_id: None}, synchronize_session=False
        )

        admin = db.query(User).filter(User.id == current_admin_id).first()
        AuditService.log_event(
            db, action="ADMIN_USER_DELETED", entity_name="users", actor_user_id=current_admin_id,
            actor_email=admin.email if admin else None, entity_id=str(user_id),
            details={"deleted_user_email": user.email},
        )
        db.delete(user)
        db.commit()

    @staticmethod
    def reset_user_mfa(user_id: int, current_admin_id: int, db: Session) -> dict:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Usuario con ID {user_id} no encontrado.")

        user.is_mfa_enabled = False
        user.totp_secret = None
        user.auth_version = int(getattr(user, "auth_version", 0) or 0) + 1
        user.updated_at = datetime.now(timezone.utc)
        db.query(MFABackupCode).filter(MFABackupCode.user_id == user_id).delete(synchronize_session=False)

        admin = db.query(User).filter(User.id == current_admin_id).first()
        AuditService.log_event(
            db, action="ADMIN_MFA_RESET", entity_name="users", actor_user_id=current_admin_id,
            actor_email=admin.email if admin else None, entity_id=str(user_id),
            details={"target_email": user.email, "auth_version": user.auth_version},
        )
        user_email = user.email
        db.commit()
        EmailService.send_mfa_reset_notification_email(email=user_email)
        return {"message": f"MFA para el usuario ID {user_id} reseteado exitosamente."}

    @staticmethod
    def list_audit_logs(db: Session, limit: int = 100, offset: int = 0) -> List[AuditLogResponse]:
        logs = AuditService.list_logs(db, limit=limit, offset=offset)
        return [AuditLogResponse.model_validate(log) for log in logs]
