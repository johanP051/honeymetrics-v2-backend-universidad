from fastapi import APIRouter

# Depends para dependencias como get_db, HTTPException para lanzar errores como 401, status para crear codigos HTTP
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import create_access_token # importa la funcion que genera el JWT
from app.db.session import get_db # proporciona la sesion de la BD
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MfaSetupResponse,
    MfaTokenResponse,
    MfaVerifyLoginRequest,
    MfaVerifyRequest,
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
from app.api.deps import get_current_user
from fastapi import Request

# APIRouter es la herramienta que me permite agrupar rutas de FastAPI
# router = APIRouter(...) crea un grupo de rutas, en este caso para autenticacion
# prefix="/auth" Hace que todas las rutas de este archivo empiecen con /auth
# tags=["Authentication"] Agrupa esas rutas con el nombre Authentication en Swagger (Documentacion)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# "/login" indica la ruta, con el el prefix='/auth' queda /auth/login
#TokenResponse es lo que le devuelve el servidor al cliente

# la funcion login espera que el cliente le envie datos que cumplan la estructura del schema LoginRequest, por ejemplo, el cliente le va a enviar un JSON, el schema valida si cumple con la estructura y si cumple lo convierte a un objeto de tipo LoginRequest
# Entrada: credentials es un LoginRequest (del cliente)
# Inyeccion, db es una Session de get_db()
# Salida: la funcion devuelve un TokenResponse al cliente
@router.post(
        "/login",
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Credenciales inválidas"
            }
        }
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(
        db,
        str(credentials.email),
        credentials.password
    )

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

    token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return setup_mfa(db, current_user)


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
def mfa_verify(payload: MfaVerifyRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    verify_and_enable_mfa(db, current_user, payload.code)
    return {"message": "Autenticación de dos factores (2FA) activada correctamente."}


@router.post("/mfa/disable", status_code=status.HTTP_200_OK)
def mfa_disable(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    disable_mfa(db, current_user)
    return {"message": "Autenticación de dos factores (2FA) desactivada."}


@router.post("/mfa/verify-login", response_model=TokenResponse)
def mfa_verify_login(payload: MfaVerifyLoginRequest, db: Session = Depends(get_db)):
    user = verify_login_mfa(db, payload.mfa_token, payload.code)
    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """Cierra la sesion revocando el JWT actual (port de guia)."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        revoke_token(db, authorization.split(" ", 1)[1])
    return {"message": "Sesión cerrada exitosamente."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    process_password_recovery(db, str(payload.email))
    return {"message": "Si el correo existe, se envió un enlace de recuperación."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_user_password(db, payload.token, payload.new_password)
    return {"message": "Contraseña actualizada. Inicia sesión."}

# Cliente (React, Swagger, etc.)
#     |
#     | Envía: LoginRequest
#     |   {
#     |     "email": "usuario@correo.com",
#     |     "password": "123456"
#     |   }
#     v
# Servidor (FastAPI)
#     |
#     | La función login() procesa los datos
#     | Llama a authenticate_user()
#     | Genera el token
#     |
#     | Devuelve: TokenResponse
#     |   {
#     |     "access_token": "eyJ...",
#     |     "token_type": "bearer"
#     |   }
#     v
# Cliente recibe la respuesta