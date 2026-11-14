"""
Endpoints de Gestión de Perfil de Usuario.
HoneyMetrics Backend v2.0 (UDEC)
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.request_origin import resolve_request_origin
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.auth import (
    MfaDisableRequest,
    MfaDisableResponse,
    MfaVerifyRequest,
    MfaVerifyResponse,
)
from app.schemas.user_profile_schema import (
    PasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from app.services.mfa_service import disable_mfa, verify_and_enable_mfa
from app.services.user_profile_service import UserProfileService

router = APIRouter(
    prefix="/users",
    tags=["Perfil de Usuario"],
)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Obtener perfil del usuario autenticado",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Retorna la información del perfil del usuario en sesión con sus scopes vigentes."""
    return UserProfileService.build_profile_response(current_user, db)


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Actualizar perfil del usuario autenticado",
)
def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Actualiza nombres o correo propio blindado contra Mass Assignment (OWASP API3:2023)."""
    return UserProfileService.update_own_profile(current_user, payload, db)


@router.put(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Actualizar perfil del usuario autenticado (alias frontend)",
)
def update_my_profile_alias(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Ruta alias para compatibilidad retroactiva con clientes web SPA."""
    return UserProfileService.update_own_profile(current_user, payload, db)


@router.put(
    "/me/password",
    summary="Cambiar contraseña del usuario autenticado",
)
def change_my_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Cambia contraseña propia, incrementa auth_version y emite nuevo token Bearer."""
    return UserProfileService.change_own_password(current_user, payload, db)


@router.post(
    "/me/mfa/verify",
    response_model=MfaVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar código de 6 dígitos y activar 2FA (alias)",
)
def verify_mfa_alias(
    payload: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activa 2FA, genera los 8 códigos de respaldo y emite token renovado."""
    return verify_and_enable_mfa(db, current_user, payload.code)


@router.post(
    "/me/mfa/disable",
    response_model=MfaDisableResponse,
    status_code=status.HTTP_200_OK,
    summary="Desactivar 2FA del usuario en sesión (alias)",
)
def disable_mfa_alias(
    request: Request,
    payload: Optional[MfaDisableRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Desactiva 2FA, purga códigos de respaldo y emite access token renovado."""
    return disable_mfa(db, current_user, payload, base_origin=resolve_request_origin(request))

