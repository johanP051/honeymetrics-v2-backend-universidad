"""
Dependencias compartidas de FastAPI para inyección en endpoints.

Proporciona guardas Zero-Trust de autenticación y autorización PBAC:
  - get_current_user: extrae y valida el JWT, valida auth_version, enjaula must_change_password,
    rechaza tokens con mfa_pending e intersecta scopes del rol en base de datos.
  - require_admin_user: restringe el acceso a usuarios con privilegio 'admin:all'.
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.permissions import get_scopes_for_role
from app.db.session import get_db
from app.models.user_model import User
from app.models.role_model import Role
from app.models.revoked_token_model import RevokedToken

bearer_scheme = HTTPBearer(auto_error=False)

ALLOWED_CAGE_PATHS = frozenset({
    "/api/v1/users/me",
    "/api/v1/users/me/profile",
    "/api/v1/users/me/password",
    "/api/v1/auth/logout",
    "/api/v1/auth/change-password",
})


def _extract_token_str(
    token_bearer: Optional[HTTPAuthorizationCredentials],
    request: Optional[Request],
) -> Optional[str]:
    """Extrae la cadena Bearer del esquema de seguridad o del header HTTP."""
    if token_bearer and token_bearer.credentials:
        return token_bearer.credentials.strip()
    if request:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                return auth_header.split(" ", 1)[1].strip()
            return auth_header.strip()
    return None


def get_current_user(
    security_scopes: SecurityScopes = SecurityScopes(),
    token_bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    request: Request = None,
    db: Session = Depends(get_db),
) -> User:
    """Extrae y valida el JWT verificando auth_version, mfa_pending, confinamiento y PBAC."""
    token = _extract_token_str(token_bearer, request)
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

    # 1. Rechazar tokens en estado MFA incompleto
    sub_str = str(payload.get("sub", ""))
    if payload.get("mfa_pending") is True or payload.get("type") == "mfa_pending" or sub_str.startswith("mfa:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación incompleta: se requiere verificación de segundo factor (MFA).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verificar lista de tokens revocados (jti)
    if "jti" in payload:
        revoked = db.query(RevokedToken).filter(RevokedToken.token_jti == payload["jti"]).first()
        if revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión cerrada. Inicia sesión de nuevo.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        user_id = int(sub_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en el token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
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

    # 3. Validación de versión de autenticación (auth_version)
    token_auth_version = int(payload.get("auth_version", 0))
    user_auth_version = int(getattr(user, "auth_version", 0) or 0)
    if token_auth_version != user_auth_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión invalidada por cambio de credenciales o estado de seguridad.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Enjaulado Server-Side de must_change_password
    must_change = bool(getattr(user, "must_change_password", False))
    require_change = bool(getattr(settings, "REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN", True))
    if must_change and require_change and request and hasattr(request, "url") and hasattr(request.url, "path"):
        norm_path = request.url.path.rstrip("/")
        if norm_path not in ALLOWED_CAGE_PATHS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe actualizar su contraseña temporal antes de acceder a otros recursos.",
            )

    # 5. Cálculo e intersección de scopes con la base de datos (Zero-Trust PBAC)
    role = None
    if getattr(user, "role_id", None) and db:
        role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role and getattr(user, "role", None):
        role = user.role
    role_name = getattr(role, "name", None) if role else None
    role_scopes = get_scopes_for_role(role_name)

    token_scopes_raw = payload.get("scopes")
    if token_scopes_raw is not None and len(token_scopes_raw) > 0:
        effective_scopes = [s for s in token_scopes_raw if s in role_scopes]
    else:
        effective_scopes = role_scopes

    if security_scopes.scopes and "admin:all" not in effective_scopes:
        for required_scope in security_scopes.scopes:
            if required_scope not in effective_scopes:
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
    """Guarda de autorización para administradores. Evalúa privilegios PBAC ('admin:all')."""
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
