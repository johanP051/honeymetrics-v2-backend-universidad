"""
Endpoints del Threat Intelligence Center — Blacklist CRUD.
Todos los endpoints de escritura (POST, PUT, DELETE) requieren rol Administrador.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin_user
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.blacklist_schema import (
    BlacklistEntryCreate,
    BlacklistEntryUpdate,
    BlacklistEntryResponse,
)
from app.services.blacklist_service import BlacklistService

router = APIRouter(
    prefix="/blacklist",
    tags=["Blacklist — Threat Center CRUD"],
)


@router.get(
    "/",
    response_model=List[BlacklistEntryResponse],
    summary="Listar todas las IPs en la Blacklist (ordenadas por threat score)",
)
def list_blacklist(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BlacklistEntryResponse]:
    """
    Retorna la lista completa de IPs registradas en el Threat Intelligence Center,
    ordenadas por threat_score descendente. Requiere estar autenticado.
    """
    return BlacklistService.get_all(db)


@router.post(
    "/",
    response_model=BlacklistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nueva IP en la Blacklist [ADMIN]",
)
def create_blacklist_entry(
    payload: BlacklistEntryCreate,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> BlacklistEntryResponse:
    """
    Registra una nueva IP en el Threat Intelligence Center.
    Aplica validación de Whitelist interna (RFC 1918, DNS públicos, loopback)
    y auto-calcula el status según el threat_score (> 70 → "Bloqueada").
    Requiere rol Administrador.
    """
    return BlacklistService.create(payload, db, admin_user_id=current_admin.id)


@router.put(
    "/{entry_id}",
    response_model=BlacklistEntryResponse,
    summary="Actualizar entrada de la Blacklist [ADMIN]",
)
def update_blacklist_entry(
    entry_id: int,
    payload: BlacklistEntryUpdate,
    _current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> BlacklistEntryResponse:
    """
    Actualiza campos de una IP existente en la Blacklist.
    Si se modifica el threat_score, recalcula el status automáticamente.
    Requiere rol Administrador.
    """
    return BlacklistService.update(entry_id, payload, db)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar IP de la Blacklist [ADMIN]",
)
def delete_blacklist_entry(
    entry_id: int,
    _current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Elimina permanentemente una entrada del Threat Intelligence Center.
    Requiere rol Administrador.
    """
    BlacklistService.delete(entry_id, db)
    return {"message": f"Entrada ID {entry_id} eliminada de la Blacklist exitosamente."}
