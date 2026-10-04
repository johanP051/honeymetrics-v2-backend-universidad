"""
Dependencias compartidas de FastAPI para inyección en endpoints.

Proporciona guardas de autenticación y autorización (RBAC) reutilizables:
  - get_current_user: extrae y valida el JWT, devuelve el User activo.
  - require_admin_user: restringe el acceso a usuarios con rol "Administrador".
"""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user_model import User
from app.models.role_model import Role


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extrae el Bearer token del header Authorization, lo decodifica y
    retorna el usuario activo asociado al JWT.

    Lanza:
      - HTTP 401 si no hay token, el token es inválido o el usuario no existe.
      - HTTP 403 si el usuario está suspendido.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Token de acceso no proporcionado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
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

    return user


def require_admin_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Guarda de autorización RBAC: permite el acceso únicamente a usuarios
    con rol "Administrador". Lanza HTTP 403 si el rol no coincide.
    """
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    # Acepta 'admin' (seed scripts) y 'Administrador' (panel) sin distinción
    # de mayúsculas: ambos identifican el rol administrador del sistema.
    if not role or role.name.strip().lower() not in ("admin", "administrador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requieren privilegios de Administrador.",
        )
    return current_user
