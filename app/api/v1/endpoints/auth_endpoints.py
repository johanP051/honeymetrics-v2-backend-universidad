from fastapi import APIRouter

# Depends para dependencias como get_db, HTTPException para lanzar errores como 401, status para crear codigos HTTP
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import (
    create_access_token,
)  # importa la funcion que genera el JWT
from app.db.session import get_db  # proporciona la sesion de la BD
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user

# APIRouter es la herramienta que me permite agrupar rutas de FastAPI
# router = APIRouter(...) crea un grupo de rutas, en este caso para autenticacion
# prefix="/auth" Hace que todas las rutas de este archivo empiecen con /auth
# tags=["Authentication"] Agrupa esas rutas con el nombre Authentication en Swagger (Documentacion)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# "/login" indica la ruta, con el el prefix='/auth' queda /auth/login
# TokenResponse es lo que le devuelve el servidor al cliente


# la funcion login espera que el cliente le envie datos que cumplan la estructura del schema LoginRequest, por ejemplo, el cliente le va a enviar un JSON, el schema valida si cumple con la estructura y si cumple lo convierte a un objeto de tipo LoginRequest
# Entrada: credentials es un LoginRequest (del cliente)
# Inyeccion, db es una Session de get_db()
# Salida: la funcion devuelve un TokenResponse al cliente
@router.post(
    "/login",
    response_model=TokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales inválidas"}},
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, str(credentials.email), credentials.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


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
