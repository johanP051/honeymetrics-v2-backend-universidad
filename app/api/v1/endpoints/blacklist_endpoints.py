"""
Endpoints del Threat Intelligence Center — Blacklist CRUD y Bóveda Forense.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin_user
from app.db.session import get_db
from app.models.user_model import User
from app.schemas.blacklist_schema import (
    BlacklistEntryCreate,
    BlacklistEntryUpdate,
    BlacklistEntryResponse,
)
from app.schemas.threat_schema import BlacklistVaultResponse
from app.services.blacklist_service import BlacklistService

router = APIRouter(
    tags=["Blacklist — Threat Center CRUD"],
)


@router.get(
    "",
    include_in_schema=False,
    response_model=List[BlacklistEntryResponse],
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
    """Retorna la lista completa de IPs registradas en el Threat Intelligence Center."""
    return BlacklistService.get_all(db)


@router.get(
    "/vault",
    response_model=List[BlacklistVaultResponse],
    summary="Consultar Bóveda Forense de Lista Negra",
)
def get_blacklist_vault(
    limit: int = Query(100, ge=1, le=500, description="Límite de registros a retornar"),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    _current_user: User = Security(get_current_user, scopes=["blacklist:read"]),
    db: Session = Depends(get_db),
) -> List[BlacklistVaultResponse]:
    """
    Retorna los registros archivados en la Bóveda Forense Inmutable de Lista Negra
    con paginación. Requiere scope 'blacklist:read'.
    """
    return BlacklistService.get_vault(db=db, limit=limit, offset=offset)


@router.post(
    "",
    include_in_schema=False,
    response_model=BlacklistEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
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
    """Registra una nueva IP en la Blacklist aplicando invariantes y PoLP."""
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
    """Actualiza campos de una IP existente en la Blacklist."""
    return BlacklistService.update(entry_id, payload, db)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar IP de la Blacklist [ADMIN]",
)
def delete_blacklist_entry(
    entry_id: int,
    current_admin: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Elimina permanentemente una entrada de la Blacklist y la archiva en la Bóveda Forense.
    Requiere rol Administrador.
    """
    BlacklistService.delete(entry_id, db, deleted_by_user_id=current_admin.id)
    return {"message": f"Entrada ID {entry_id} eliminada de la Blacklist exitosamente."}
