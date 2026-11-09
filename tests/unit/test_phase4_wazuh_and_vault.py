"""
Tests de Integración y Calidad para Fase 4:
Extracción en Cascada de Country en Wazuh, Bóveda Forense (Vault) y Quality Gate.
HoneyMetrics Backend v2.0 (UDEC)
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AuditLog, BlacklistEntry, BlacklistAuditVault, Role, User
from app.schemas.threat_schema import AttackerIPSchema, BlacklistVaultResponse
from app.services.wazuh_extractor import extract_country_from_hit, WazuhExtractor


@pytest.fixture
def phase4_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        admin_role = Role(name="Administrador", description="Admin general")
        analyst_role = Role(name="Analista", description="Analista SOC")
        session.add_all([admin_role, analyst_role])
        session.flush()

        admin = User(
            email="admin.phase4@ucundinamarca.edu.co",
            first_names="Admin", last_names="Docente",
            hashed_password=hash_password("AdminSecurePassword123"),
            role_id=admin_role.id, is_active=True, must_change_password=False, auth_version=0,
        )
        analyst = User(
            email="analyst.phase4@ucundinamarca.edu.co",
            first_names="Analyst", last_names="SOC",
            hashed_password=hash_password("AnalystPassword123"),
            role_id=analyst_role.id, is_active=True, must_change_password=False, auth_version=0,
        )
        session.add_all([admin, analyst])
        session.commit()
        yield session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(phase4_db):
    app.dependency_overrides[get_db] = lambda: phase4_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_extract_country_from_hit_cascade():
    """Verifica la cascada de resolución de país desde hits heterogéneos de Wazuh/OpenSearch."""
    # 1. GeoLocation.country_name tiene máxima prioridad
    hit_geo = {"GeoLocation": {"country_name": "China"}, "data": {"abuseipdb": {"country": "CN"}}}
    assert extract_country_from_hit(hit_geo) == "China"

    # 2. data.abuseipdb.country si no hay GeoLocation
    hit_abuse = {"data": {"abuseipdb": {"country": "Germany"}}}
    assert extract_country_from_hit(hit_abuse) == "Germany"

    # 3. data.abuseipdb.country_code
    hit_code = {"data": {"abuseipdb": {"country_code": "CN"}}}
    assert extract_country_from_hit(hit_code) == "CN"

    # 4. data.country plano
    hit_data = {"data": {"country": "United States"}}
    assert extract_country_from_hit(hit_data) == "United States"

    # 5. Fallback seguro ante hit vacío o inválido
    assert extract_country_from_hit({}) == "Unknown"
    assert extract_country_from_hit(None) == "Unknown"


def test_attacker_ip_schema_country_field():
    """Valida el campo country en AttackerIPSchema con valor por defecto y explícito."""
    item_default = AttackerIPSchema(
        ip="185.220.101.5", total_events=120, threat_score=80, badge="APT",
        primary_tactic="Initial Access", avg_severity=6.0,
    )
    assert item_default.country == "Unknown"

    item_explicit = AttackerIPSchema(
        ip="185.220.101.5", country="Netherlands", total_events=120,
        threat_score=80, badge="APT", primary_tactic="Initial Access", avg_severity=6.0,
    )
    assert item_explicit.country == "Netherlands"


def test_delete_blacklist_creates_vault_and_audit(client, phase4_db):
    """Verifica que eliminar una IP mediante DELETE archiva en vault y registra en audit_logs."""
    login = client.post("/api/v1/auth/login", json={"email": "admin.phase4@ucundinamarca.edu.co", "password": "AdminSecurePassword123"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # 1. Crear entrada en la lista negra
    create_resp = client.post(
        "/api/v1/threats/blacklist/",
        headers=headers,
        json={"ip": "45.61.186.9", "threat_score": 92, "category": "Botnet Storm", "notes": "C2 node"},
    )
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    # 2. Eliminar entrada mediante ruta /threats/blacklist/{id}
    del_resp = client.delete(f"/api/v1/threats/blacklist/{entry_id}", headers=headers)
    assert del_resp.status_code == 200

    # 3. Validar presencia en BlacklistAuditVault
    vault_entry = phase4_db.query(BlacklistAuditVault).filter(BlacklistAuditVault.original_entry_id == entry_id).first()
    assert vault_entry is not None
    assert vault_entry.original_ip == "45.61.186.9"
    assert vault_entry.threat_score == 92
    assert vault_entry.status == "Bloqueada"
    assert vault_entry.deleted_by_user_id is not None

    # 4. Validar registro en AuditLog
    audit_log = phase4_db.query(AuditLog).filter(
        AuditLog.action == "BLACKLIST_IP_DELETED_APP",
        AuditLog.entity_id == str(entry_id),
    ).first()
    assert audit_log is not None
    assert audit_log.ip_address == "45.61.186.9"


def test_get_blacklist_vault_endpoint(client, phase4_db):
    """Verifica endpoint GET /api/v1/threats/blacklist/vault con RBAC y paginación."""
    login_admin = client.post("/api/v1/auth/login", json={"email": "admin.phase4@ucundinamarca.edu.co", "password": "AdminSecurePassword123"}).json()
    login_analyst = client.post("/api/v1/auth/login", json={"email": "analyst.phase4@ucundinamarca.edu.co", "password": "AnalystPassword123"}).json()

    headers_admin = {"Authorization": f"Bearer {login_admin['access_token']}"}
    headers_analyst = {"Authorization": f"Bearer {login_analyst['access_token']}"}

    # Crear y eliminar dos IPs para poblar la bóveda
    for ip, score in [("45.61.187.10", 75), ("45.61.187.20", 88)]:
        cr = client.post("/api/v1/threats/blacklist/", headers=headers_admin, json={"ip": ip, "threat_score": score, "category": "Scanner"})
        client.delete(f"/api/v1/threats/blacklist/{cr.json()['id']}", headers=headers_admin)

    # Consulta por Admin (tiene scope blacklist:read / admin:all)
    vault_resp = client.get("/api/v1/threats/blacklist/vault?limit=10&offset=0", headers=headers_admin)
    assert vault_resp.status_code == 200
    data = vault_resp.json()
    assert len(data) >= 2
    assert "original_ip" in data[0]
    assert "threat_score" in data[0]

    # Alias /api/v1/blacklist/vault permitido para Admin
    alias_resp = client.get("/api/v1/blacklist/vault?limit=1", headers=headers_admin)
    assert alias_resp.status_code == 200
    assert len(alias_resp.json()) == 1

    # Analista no participa en CU03 Lista Negra -> debe recibir 403 Forbidden
    forbidden_resp = client.get("/api/v1/threats/blacklist/vault?limit=10&offset=0", headers=headers_analyst)
    assert forbidden_resp.status_code == 403
