"""
Controlador de Autenticación, 2FA MFA TOTP, Sesión y Recuperación de Contraseñas.
HoneyMetrics Backend v2.0 (Cátedra de Ingeniería de Software - UDEC)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, get_current_user
from app.core.permissions import get_scopes_for_role
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MfaDisableResponse,
    MfaSetupResponse,
    MfaTokenResponse,
    MfaVerifyLoginRequest,
    MfaVerifyRequest,
    MfaVerifyResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    process_password_recovery,
    reset_user_password,
    revoke_token,
)
from app.services.mfa_service import (
    disable_mfa,
    mfa_login_flow,
    setup_mfa,
    verify_and_enable_mfa,
    verify_login_mfa,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales inválidas"}},
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Inicia sesión validando credenciales y derivando a flujo MFA si está habilitado."""
    user = authenticate_user(db, str(credentials.email), credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    mfa_result = mfa_login_flow(db, user)
    if mfa_result.get("mfa_required"):
        return MfaTokenResponse(
            mfa_required=True,
            mfa_token=mfa_result["mfa_token"],
        )

    role_name = user.role.name if getattr(user, "role", None) else None
    user_scopes = get_scopes_for_role(role_name)
    token = create_access_token(
        str(user.id),
        scopes=user_scopes,
        auth_version=int(user.auth_version or 0),
        role=role_name,
    )

    user_response = UserResponse.model_validate(user)
    user_response.role_name = role_name
    user_response.scopes = user_scopes

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response,
        scopes=user_scopes,
        must_change_password=bool(user.must_change_password),
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Genera o reutiliza secreto TOTP y código QR para Google Authenticator."""
    return setup_mfa(db, current_user)


@router.post("/mfa/verify", response_model=MfaVerifyResponse, status_code=status.HTTP_200_OK)
def mfa_verify(
    payload: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activa 2FA, genera los 8 códigos de respaldo SHA-256 y renueva el access token."""
    return verify_and_enable_mfa(db, current_user, payload.code)


@router.post("/mfa/disable", response_model=MfaDisableResponse, status_code=status.HTTP_200_OK)
def mfa_disable(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Desactiva 2FA, purga códigos de respaldo y emite access token renovado."""
    return disable_mfa(db, current_user)


@router.post("/mfa/verify-login", response_model=TokenResponse)
def mfa_verify_login(payload: MfaVerifyLoginRequest, db: Session = Depends(get_db)):
    """Verifica OTP o código de respaldo, quema jti y emite JWT definitivo con scopes."""
    user = verify_login_mfa(db, payload.mfa_token, payload.code)
    role_name = user.role.name if getattr(user, "role", None) else None
    user_scopes = get_scopes_for_role(role_name)
    token = create_access_token(
        str(user.id),
        scopes=user_scopes,
        auth_version=int(user.auth_version or 0),
        role=role_name,
    )
    user_response = UserResponse.model_validate(user)
    user_response.role_name = role_name
    user_response.scopes = user_scopes

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response,
        scopes=user_scopes,
        must_change_password=bool(user.must_change_password),
        mfa_required=False,
    )


@router.post("/login/mfa-verify", response_model=TokenResponse, summary="Alias de verificación MFA")
def login_mfa_verify_alias(payload: MfaVerifyLoginRequest, db: Session = Depends(get_db)):
    """Ruta alias para compatibilidad retroactiva con clientes que consumen /login/mfa-verify."""
    return mfa_verify_login(payload=payload, db=db)


@router.post("/logout", summary="Cerrar sesión y revocar token [AUTH]")
def logout(
    _current_user: User = Depends(get_current_user),
    token_bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Cierra sesión revocando el identificador jti del JWT en base de datos."""
    token: Optional[str] = None
    if token_bearer and token_bearer.credentials:
        token = token_bearer.credentials
    elif request:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else auth_header.strip()

    if token:
        revoke_token(db, token)
    return {"message": "Sesión cerrada exitosamente."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Envía correo con token para restablecer contraseña si el usuario existe."""
    process_password_recovery(db, str(payload.email))
    return {"message": "Si el correo existe, se envió un enlace de recuperación."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Restablece la contraseña validando la política ASVS e invalidando sesiones previas."""
    reset_user_password(db, payload.token, payload.new_password)
    return {"message": "Contraseña actualizada. Inicia sesión."}