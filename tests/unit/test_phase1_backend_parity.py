"""
Pruebas RDD para Fase 1: Paridad de Endpoints, JWT Claims y Correos Anti-Dark-Mode.
HoneyMetrics Backend v2.0 (UDEC)
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, require_admin_user
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.auth import MfaVerifyLoginRequest, TokenResponse, UserResponse
from app.services.email_service import EmailService

client = TestClient(app)


def test_jwt_role_and_role_name_claims():
    """Verifica que create_access_token incluya role y role_name en el payload decodificado."""
    token = create_access_token(
        subject="42",
        scopes=["dashboard:read", "admin:all"],
        auth_version=1,
        role="Administrador",
    )
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "Administrador"
    assert payload["role_name"] == "Administrador"
    assert "admin:all" in payload["scopes"]


def test_jwt_role_from_dict_subject():
    """Verifica que create_access_token con dict preserve o sincronice role y role_name."""
    token = create_access_token(
        subject={"sub": "99", "role": "Analista"},
    )
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["role"] == "Analista"
    assert payload["role_name"] == "Analista"


def test_token_response_schema_must_change_password_at_root():
    """Verifica que TokenResponse contenga must_change_password en la raíz."""
    user_dto = UserResponse(
        id=1,
        email="test@ucundinamarca.edu.co",
        first_names="Admin",
        last_names="Root",
        role_id=1,
        role_name="Administrador",
        is_active=True,
        must_change_password=False,
        scopes=["admin:all"],
    )
    resp = TokenResponse(
        access_token="fake_token",
        user=user_dto,
        must_change_password=False,
    )
    assert resp.must_change_password is False
    assert resp.user.must_change_password is False


def test_mfa_verify_login_request_supports_code_and_totp_code():
    """Verifica que el DTO acepte tanto 'code' como el alias 'totp_code'."""
    req1 = MfaVerifyLoginRequest(mfa_token="token123", code="123456")
    assert req1.code == "123456"

    req2 = MfaVerifyLoginRequest(mfa_token="token123", totp_code="654321")
    assert req2.code == "654321"

    req3 = MfaVerifyLoginRequest(mfa_token="token123", totp_code="ABCD-EFGH")
    assert req3.code == "ABCD-EFGH"


def test_root_health_check_endpoint():
    """Verifica que GET /api/v1/health responda 200 OK con el esquema oficial."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "HoneyMetrics" in data["service"]


def test_executive_dashboard_report_endpoint():
    """Verifica que GET /api/v1/dashboard/report/executive devuelva métricas consolidadas."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "directivo@ucundinamarca.edu.co"
    mock_user.is_active = True
    mock_user.must_change_password = False
    mock_user.auth_version = 0

    role = MagicMock(spec=Role)
    role.name = "Directivo"
    mock_user.role = role

    from app.db.session import get_db
    from app.services.dashboard_service import DashboardService

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        mock_data = {
            "summary": {
                "total_threats_tracked": 12,
                "active_blocks": 5,
                "registered_users": 3,
                "total_forensic_exports": 2,
                "average_threat_score": 68.5,
            },
            "threat_landscape": {
                "top_countries": [{"country": "Colombia", "count": 10}],
                "top_threats": [{"ip": "1.2.3.4", "score": 85, "category": "Botnet", "status": "Bloqueada"}],
            },
        }
        with patch.object(DashboardService, "get_executive_report", return_value=mock_data):
            response = client.get("/api/v1/dashboard/report/executive")
            assert response.status_code == 200
            data = response.json()
            assert "summary" in data
            assert "threat_landscape" in data
            assert data["summary"]["total_threats_tracked"] == 12
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_threats_center_summary_alias_route():
    """Verifica que GET /api/v1/threats-center/summary responda igual que /threats/summary."""
    from app.db.session import get_db
    from app.services.threat_service import ThreatService

    mock_user = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(ThreatService, "get_threat_summary") as mock_summary:
            from app.schemas.threat_schema import ThreatSummarySchema
            mock_summary.return_value = ThreatSummarySchema(
                total_analyzed_events=50000,
                unique_attacker_ips=100,
                persistent_threats_count=5,
                active_critical_cves_count=10,
                peak_hour_utc="14:00 - 15:00 UTC",
            )
            response = client.get("/api/v1/threats-center/summary")
            assert response.status_code == 200
            data = response.json()
            assert "total_analyzed_events" in data
            assert data["total_analyzed_events"] == 50000
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_threats_center_blacklist_and_vault_routes():
    """Verifica que las rutas de Blacklist y Bóveda respondan bajo /threats-center."""
    from app.db.session import get_db
    from app.services.blacklist_service import BlacklistService

    mock_user = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(BlacklistService, "get_all", return_value=[]), \
             patch.object(BlacklistService, "get_vault", return_value=[]):
            res_list = client.get("/api/v1/threats-center/")
            assert res_list.status_code == 200
            assert isinstance(res_list.json(), list)

            res_vault = client.get("/api/v1/threats-center/vault")
            assert res_vault.status_code == 200
            assert isinstance(res_vault.json(), list)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_admin_roles_alias_route():
    """Verifica que GET /api/v1/admin/roles y GET /api/v1/roles respondan con la lista de roles."""
    from app.db.session import get_db
    from app.services.role_service import RoleService

    mock_user = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(RoleService, "list_roles_with_counts", return_value=[]):
            res1 = client.get("/api/v1/roles")
            res2 = client.get("/api/v1/admin/roles")
            assert res1.status_code == 200
            assert res2.status_code == 200
            assert res1.json() == res2.json()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_admin_users_alias_route():
    """Verifica que GET /api/v1/users responda con la lista de usuarios bajo credenciales admin."""
    from app.db.session import get_db
    from app.services.admin_service import AdminService

    mock_admin = MagicMock()
    app.dependency_overrides[require_admin_user] = lambda: mock_admin
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch.object(AdminService, "list_users", return_value=[]):
            res_admin = client.get("/api/v1/admin/users")
            res_users = client.get("/api/v1/users")
            assert res_admin.status_code == 200
            assert res_users.status_code == 200
            assert res_admin.json() == res_users.json()
    finally:
        app.dependency_overrides.pop(require_admin_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_email_mfa_reset_notification():
    """Verifica que send_mfa_reset_notification_email arme el correo con logo y aviso de seguridad."""
    with patch("app.core.config.settings.RESEND_API_KEY", "re_test_mfa_key"):
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "mfa_reset_123"}
            ok = EmailService.send_mfa_reset_notification_email("usuario@ucundinamarca.edu.co")
            assert ok is True
            assert mock_send.call_count == 1
            call_params = mock_send.call_args[0][0]
            html = call_params["html"]
            assert "HoneyMetrics_logo_circled" in html
            assert "Restablecimiento de 2FA" in html
            assert "no respondas a este mensaje" in html
