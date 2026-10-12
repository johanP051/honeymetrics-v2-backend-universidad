"""
Dependencias compartidas de FastAPI para inyección en endpoints.

Proporciona guardas de autenticación y autorización (RBAC) reutilizables:
  - get_current_user: extrae y valida el JWT, devuelve el User activo.
  - require_admin_user: restringe el acceso a usuarios con rol "Administrador".
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.permissions import get_scopes_for_role
from app.db.session import get_db
from app.models.user_model import User
from app.models.role_model import Role

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    security_scopes: SecurityScopes = SecurityScopes(),
    token_bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
) -> User:
    """
    Extrae el Bearer token del header Authorization, lo decodifica y
    retorna el usuario activo asociado al JWT verificando permisos PBAC (scopes).

    Soporta:
      - Autenticación Swagger UI (vía esquema nativo Bearer y botón Authorize).
      - Header 'Authorization: Bearer <token>' estándar.
      - Fallback flexible si el token se envía sin el prefijo 'Bearer '.

    Lanza:
      - HTTP 401 si no hay token, el token es inválido o el usuario no existe.
      - HTTP 403 si el usuario está suspendido o carece de los scopes requeridos.
    """
    token: Optional[str] = None
    if token_bearer and token_bearer.credentials:
        token = token_bearer.credentials
    elif request:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            if auth_header.startswith("Bearer ") or auth_header.startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
            else:
                token = auth_header.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Token de acceso no proporcionado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if "jti" in payload:
        from app.models.revoked_token_model import RevokedToken

        revoked = db.query(RevokedToken).filter(RevokedToken.token_jti == payload["jti"]).first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión cerrada. Inicia sesión de nuevo.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_id: str = payload["sub"]
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado en el sistema.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario se encuentra suspendida o inactiva.",
        )

    # Verificación de Scopes (PBAC) sin hardcoding
    if security_scopes.scopes:
        role_name = user.role.name if getattr(user, "role", None) else None
        token_scopes = payload.get("scopes") or get_scopes_for_role(role_name)

        if "admin:all" not in token_scopes:
            for required_scope in security_scopes.scopes:
                if required_scope not in token_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permisos insuficientes: se requiere el scope '{required_scope}'.",
                        headers={"WWW-Authenticate": f'Bearer scope="{required_scope}"'},
                    )

    return user


def require_admin_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Guarda de autorización compatible hacia atrás.
    Evalúa scopes PBAC ('admin:all') garantizando cero hardcoding.
    """
    role = None
    if getattr(current_user, "role_id", None) and db:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
    
    if not role and getattr(current_user, "role", None):
        role = current_user.role

    role_name = getattr(role, "name", None) if role else None
    user_scopes = get_scopes_for_role(role_name)

    if "admin:all" not in user_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requieren privilegios de Administrador (admin:all).",
        )
    return current_user
