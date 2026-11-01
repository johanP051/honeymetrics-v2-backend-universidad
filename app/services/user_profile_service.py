"""
UserProfileService — Capa de servicio para perfil de usuario y cambio de contraseña.
HoneyMetrics Backend v2.0 (UDEC)
"""
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.password_policy import validate_new_password
from app.core.permissions import get_scopes_for_role
from app.core.security import create_access_token, hash_password, verify_password
from app.models.audit_log_model import AuditLog
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.user_profile_schema import (
    PasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)


class UserProfileService:
    @staticmethod
    def build_profile_response(user: User, db: Session) -> UserProfileResponse:
        """Construye el DTO de perfil resolviendo rol y scopes vigentes."""
        role = user.role or db.query(Role).filter(Role.id == user.role_id).first()
        role_name = role.name if role else "Sin Rol"
        scopes = get_scopes_for_role(role_name)
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            first_names=user.first_names,
            last_names=user.last_names,
            role_id=user.role_id,
            role_name=role_name,
            is_active=user.is_active,
            is_mfa_enabled=bool(user.is_mfa_enabled),
            must_change_password=bool(user.must_change_password),
            scopes=scopes,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @classmethod
    def update_own_profile(
        cls, user: User, payload: UserProfileUpdateRequest, db: Session
    ) -> UserProfileResponse:
        """Actualiza nombres y/o email propio con validación de colisión y auditoría."""
        changes: dict[str, dict[str, str]] = {}
        if payload.first_names is not None and payload.first_names != user.first_names:
            changes["first_names"] = {"old": user.first_names, "new": payload.first_names}
            user.first_names = payload.first_names

        if payload.last_names is not None and payload.last_names != user.last_names:
            changes["last_names"] = {"old": user.last_names, "new": payload.last_names}
            user.last_names = payload.last_names

        if payload.email is not None:
            norm_email = str(payload.email).strip().lower()
            if norm_email != user.email.lower():
                existing = db.query(User).filter(
                    User.email.ilike(norm_email), User.id != user.id
                ).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"El correo '{norm_email}' ya está registrado por otro usuario.",
                    )
                changes["email"] = {"old": user.email, "new": norm_email}
                user.email = norm_email

        if changes:
            user.updated_at = datetime.now(timezone.utc)
            db.add(
                AuditLog(
                    actor_user_id=user.id,
                    actor_email=user.email,
                    action="USER_PROFILE_UPDATED",
                    entity_name="users",
                    entity_id=str(user.id),
                    details=changes,
                )
            )
            db.commit()
            db.refresh(user)

        return cls.build_profile_response(user, db)

    @classmethod
    def change_own_password(
        cls, user: User, payload: PasswordChangeRequest, db: Session
    ) -> dict:
        """Rota la contraseña del usuario, incrementa auth_version y emite nuevo JWT."""
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta.",
            )

        normalized_pwd = validate_new_password(
            payload.new_password, current_password=payload.current_password
        )
        user.hashed_password = hash_password(normalized_pwd)
        user.must_change_password = False
        user.auth_version = int(getattr(user, "auth_version", 0) or 0) + 1
        user.updated_at = datetime.now(timezone.utc)

        db.add(
            AuditLog(
                actor_user_id=user.id,
                actor_email=user.email,
                action="USER_PASSWORD_CHANGED",
                entity_name="users",
                entity_id=str(user.id),
                details={"auth_version": user.auth_version},
            )
        )
        db.commit()
        db.refresh(user)

        role = user.role or db.query(Role).filter(Role.id == user.role_id).first()
        role_name = role.name if role else None
        user_scopes = get_scopes_for_role(role_name)
        new_token = create_access_token(
            subject=str(user.id),
            scopes=user_scopes,
            auth_version=user.auth_version,
        )

        return {
            "access_token": new_token,
            "token_type": "bearer",
            "message": "Contraseña actualizada exitosamente.",
        }
