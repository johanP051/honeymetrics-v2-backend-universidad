"""
Tests unitarios y de integración para la Gestión de Roles (RoleService & Endpoints).

Cubre:
  - Listar roles con conteo de usuarios y auto-sembrado canónico.
  - Creación de roles con validación de unicidad.
  - Eliminación de roles:
      * Rechazo de eliminación del rol crítico "Administrador".
      * Rechazo de eliminación de roles con usuarios asociados.
      * Eliminación exitosa de roles huérfanos.
  - Protección RBAC / PBAC en los endpoints de roles.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.role_schema import RoleCreateRequest, RoleItemResponse
from app.services.role_service import RoleService
from app.api.deps import get_current_user

client = TestClient(app)

MOCK_ADMIN = MagicMock(spec=User)
MOCK_ADMIN.id = 1
MOCK_ADMIN.email = "admin@honeymetrics.io"
MOCK_ADMIN.is_active = True
MOCK_ADMIN.role_id = 1
MOCK_ADMIN_ROLE = MagicMock(spec=Role)
MOCK_ADMIN_ROLE.name = "Administrador"
MOCK_ADMIN.role = MOCK_ADMIN_ROLE

MOCK_ANALYST = MagicMock(spec=User)
MOCK_ANALYST.id = 2
MOCK_ANALYST.email = "analyst@honeymetrics.io"
MOCK_ANALYST.is_active = True
MOCK_ANALYST.role_id = 2
MOCK_ANALYST_ROLE = MagicMock(spec=Role)
MOCK_ANALYST_ROLE.name = "Analista"
MOCK_ANALYST.role = MOCK_ANALYST_ROLE


# ─── Service Layer Unit Tests ──────────────────────────────────────────────────

def test_seed_canonical_roles_creates_missing():
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = None

    RoleService.seed_canonical_roles_if_needed(mock_db)

    assert mock_db.add.call_count == 4
    assert mock_db.commit.called


def test_list_roles_with_counts():
    mock_db = MagicMock()
    mock_role_1 = MagicMock()
    mock_role_1.id = 1
    mock_role_1.name = "Administrador"
    mock_role_1.description = "Admin desc"

    mock_role_2 = MagicMock()
    mock_role_2.id = 2
    mock_role_2.name = "Analista"
    mock_role_2.description = "Analyst desc"
    
    mock_db.query(Role).order_by().all.return_value = [mock_role_1, mock_role_2]
    mock_db.query(User).filter().count.side_effect = [3, 1]

    with patch.object(RoleService, "seed_canonical_roles_if_needed"):
        roles = RoleService.list_roles_with_counts(mock_db)

    assert len(roles) == 2
    assert roles[0].name == "Administrador"
    assert roles[0].user_count == 3
    assert roles[1].name == "Analista"
    assert roles[1].user_count == 1


def test_create_role_success():
    mock_db = MagicMock()
    mock_db.query(Role).filter().first.return_value = None

    def fake_refresh(obj):
        obj.id = 10

    mock_db.refresh.side_effect = fake_refresh

    payload = RoleCreateRequest(name="Auditor Externo", description="Acceso a reportes")
    
    with patch.object(RoleService, "seed_canonical_roles_if_needed"):
        result = RoleService.create_role(payload, mock_db)

    assert mock_db.add.called
    assert mock_db.commit.called
    assert result.id == 10
    assert result.name == "Auditor Externo"
    assert result.user_count == 0


def test_create_role_duplicate_name_raises_400():
    mock_db = MagicMock()
    existing_role = MagicMock()
    existing_role.id = 5
    existing_role.name = "Auditor"
    mock_db.query(Role).filter().first.return_value = existing_role

    payload = RoleCreateRequest(name="auditor", description="Repetido")
    
    with patch.object(RoleService, "seed_canonical_roles_if_needed"):
        with pytest.raises(HTTPException) as exc_info:
            RoleService.create_role(payload, mock_db)

    assert exc_info.value.status_code == 400
    assert "Ya existe un rol" in exc_info.value.detail


def test_delete_role_not_found_raises_404():
    mock_db = MagicMock()
    mock_db.query(Role).filter().first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        RoleService.delete_role(999, mock_db)

    assert exc_info.value.status_code == 404
    assert "no existe" in exc_info.value.detail


def test_delete_role_admin_protected_raises_400():
    mock_db = MagicMock()
    admin_role = MagicMock()
    admin_role.id = 1
    admin_role.name = "Administrador"
    mock_db.query(Role).filter().first.return_value = admin_role

    with pytest.raises(HTTPException) as exc_info:
        RoleService.delete_role(1, mock_db)

    assert exc_info.value.status_code == 400
    assert "no puede ser eliminado" in exc_info.value.detail


def test_delete_role_with_active_users_raises_400():
    mock_db = MagicMock()
    role_to_delete = MagicMock()
    role_to_delete.id = 2
    role_to_delete.name = "Analista"
    mock_db.query(Role).filter().first.return_value = role_to_delete
    mock_db.query(User).filter().count.return_value = 4

    with pytest.raises(HTTPException) as exc_info:
        RoleService.delete_role(2, mock_db)

    assert exc_info.value.status_code == 400
    assert "tiene 4 usuario(s) asignado(s)" in exc_info.value.detail


def test_delete_role_success():
    mock_db = MagicMock()
    mock_role = MagicMock()
    mock_role.id = 5
    mock_role.name = "Temporal"
    mock_db.query(Role).filter().first.return_value = mock_role
    mock_db.query(User).filter().count.return_value = 0

    result = RoleService.delete_role(5, mock_db)

    assert result is True
    mock_db.delete.assert_called_once_with(mock_role)
    assert mock_db.commit.called


# ─── API Endpoints Tests ───────────────────────────────────────────────────────

def test_get_roles_unauthorized():
    response = client.get("/api/v1/roles")
    assert response.status_code in (401, 403)


def test_get_roles_authenticated():
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    try:
        with patch.object(
            RoleService,
            "list_roles_with_counts",
            return_value=[
                RoleItemResponse(id=1, name="Administrador", description="Admin", user_count=2),
                RoleItemResponse(id=2, name="Analista", description="Analista", user_count=1),
            ],
        ):
            response = client.get("/api/v1/roles")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Administrador"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_create_role_endpoint_admin_success():
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    try:
        with patch.object(
            RoleService,
            "create_role",
            return_value=RoleItemResponse(id=10, name="Operador SOC", description="Desc", user_count=0),
        ):
            response = client.post(
                "/api/v1/roles",
                json={"name": "Operador SOC", "description": "Desc"},
            )
            assert response.status_code == 201
            assert response.json()["name"] == "Operador SOC"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_delete_role_endpoint_admin_success():
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    try:
        with patch.object(RoleService, "delete_role", return_value=True):
            response = client.delete("/api/v1/roles/10")
            assert response.status_code == 200
            assert response.json()["message"] == "Rol eliminado exitosamente."
    finally:
        app.dependency_overrides.pop(get_current_user, None)
