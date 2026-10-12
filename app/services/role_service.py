from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.role_schema import RoleItemResponse, RoleCreateRequest


class RoleService:
    CANONICAL_ROLES = [
        {"name": "Administrador", "description": "Acceso total a gestión de usuarios, roles, logs y configuración"},
        {"name": "Analista", "description": "Acceso operativo al SOC: Threat Intelligence Center, Lista Negra y exportación"},
        {"name": "Consultor", "description": "Acceso de auditoría forense: Dashboard CTI, reglas MITRE y exportación de logs"},
        {"name": "Directivo", "description": "Acceso estratégico: Dashboards ejecutivos y visualización de reportes"},
    ]

    @classmethod
    def seed_canonical_roles_if_needed(cls, db: Session) -> None:
        """Asegura que los 4 roles canónicos existan en la base de datos."""
        for role_data in cls.CANONICAL_ROLES:
            existing = db.query(Role).filter(Role.name.ilike(role_data["name"])).first()
            if not existing:
                new_role = Role(name=role_data["name"], description=role_data["description"])
                db.add(new_role)
            elif not existing.description:
                existing.description = role_data["description"]
        db.commit()

    @classmethod
    def list_roles_with_counts(cls, db: Session) -> List[RoleItemResponse]:
        """Retorna todos los roles con el conteo de usuarios asignados a cada uno."""
        cls.seed_canonical_roles_if_needed(db)
        roles = db.query(Role).order_by(Role.id.asc()).all()
        result = []
        for r in roles:
            count = db.query(User).filter(User.role_id == r.id).count()
            result.append(
                RoleItemResponse(
                    id=r.id,
                    name=r.name,
                    description=r.description,
                    user_count=count,
                )
            )
        return result

    @classmethod
    def create_role(cls, payload: RoleCreateRequest, db: Session) -> RoleItemResponse:
        """Crea un nuevo rol asegurando unicidad del nombre."""
        cls.seed_canonical_roles_if_needed(db)
        normalized_name = payload.name.strip()
        existing = db.query(Role).filter(Role.name.ilike(normalized_name)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un rol con el nombre '{normalized_name}'.",
            )

        new_role = Role(name=normalized_name, description=payload.description)
        db.add(new_role)
        db.commit()
        db.refresh(new_role)

        return RoleItemResponse(
            id=new_role.id,
            name=new_role.name,
            description=new_role.description,
            user_count=0,
        )

    @classmethod
    def delete_role(cls, role_id: int, db: Session) -> bool:
        """Elimina un rol si no tiene usuarios asociados y no es Administrador."""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El rol con ID {role_id} no existe.",
            )

        if role.name.lower() in ["administrador", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol 'Administrador' es crítico para el sistema y no puede ser eliminado.",
            )

        user_count = db.query(User).filter(User.role_id == role_id).count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar el rol '{role.name}' porque tiene {user_count} usuario(s) asignado(s). Reasigna los usuarios antes de eliminarlo.",
            )

        db.delete(role)
        db.commit()
        return True
