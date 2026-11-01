"""
Tests de Integración y Seguridad para Fase 3:
Perfil de Usuario, Blindaje Anti-Mass Assignment, Fix FK en Deletion de 2FA y Auditoría.
HoneyMetrics Backend v2.0 (UDEC)
"""
import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AuditLog, BlacklistEntry, MFABackupCode, Role, User


@pytest.fixture
def phase3_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        admin_role = Role(name="Administrador", description="Admin general")
        analyst_role = Role(name="Analista", description="Analista SOC")
        session.add_all([admin_role, analyst_role])
        session.flush()

        admin = User(
            email="admin.phase3@ucundinamarca.edu.co",
            first_names="Admin", last_names="Principal",
            hashed_password=hash_password("AdminSecurePassword123"),
            role_id=admin_role.id, is_active=True, must_change_password=False, auth_version=0,
        )
        user = User(
            email="analyst.phase3@ucundinamarca.edu.co",
            first_names="Analyst", last_names="Junior",
            hashed_password=hash_password("AnalystPassword123"),
            role_id=analyst_role.id, is_active=True, must_change_password=False, auth_version=0,
        )
        session.add_all([admin, user])
        session.commit()
        yield session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(phase3_db):
    app.dependency_overrides[get_db] = lambda: phase3_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_user_profile_update_and_anti_mass_assignment(client):
    """Verifica actualización legítima de perfil y rechazo 422 ante Mass Assignment."""
    login = client.post("/api/v1/auth/login", json={"email": "analyst.phase3@ucundinamarca.edu.co", "password": "AnalystPassword123"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # 1. Consulta GET /users/me
    get_res = client.get("/api/v1/users/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["first_names"] == "Analyst"

    # 2. Actualización legítima PUT /users/me y alias PUT /users/me/profile
    upd_res = client.put("/api/v1/users/me", headers=headers, json={"first_names": "Carlos", "last_names": "Gómez"})
    assert upd_res.status_code == 200
    assert upd_res.json()["first_names"] == "Carlos"
    assert upd_res.json()["last_names"] == "Gómez"

    alias_res = client.put("/api/v1/users/me/profile", headers=headers, json={"first_names": "Carlos Alberto"})
    assert alias_res.status_code == 200
    assert alias_res.json()["first_names"] == "Carlos Alberto"

    # Colisión de correo existente -> 409
    dup_res = client.put("/api/v1/users/me", headers=headers, json={"email": "admin.phase3@ucundinamarca.edu.co"})
    assert dup_res.status_code == 409

    # 3. Intento de Mass Assignment (BOPLA OWASP API3:2023) -> 422
    for forbidden_field in [{"role_id": 1}, {"is_active": False}, {"is_mfa_enabled": True}, {"auth_version": 99}]:
        malicious_res = client.put("/api/v1/users/me", headers=headers, json={"first_names": "Hacker", **forbidden_field})
        assert malicious_res.status_code == 422, f"Falló bloqueo de campo: {forbidden_field}"



def test_password_change_rotates_credentials_and_issues_new_token(client):
    """Verifica cambio de contraseña, incremento de auth_version y nuevo JWT."""
    login = client.post("/api/v1/auth/login", json={"email": "analyst.phase3@ucundinamarca.edu.co", "password": "AnalystPassword123"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Cambio exitoso
    change_payload = {
        "current_password": "AnalystPassword123",
        "new_password": "NewCompliantPassword2026",
        "confirm_password": "NewCompliantPassword2026",
    }
    res = client.put("/api/v1/users/me/password", headers=headers, json=change_payload)
    assert res.status_code == 200
    new_token = res.json()["access_token"]
    assert new_token

    # Token previo debe quedar invalidado por desface de auth_version
    old_token_res = client.get("/api/v1/users/me", headers=headers)
    assert old_token_res.status_code == 401

    # Nuevo token funciona
    new_headers = {"Authorization": f"Bearer {new_token}"}
    assert client.get("/api/v1/users/me", headers=new_headers).status_code == 200


def test_delete_user_with_active_mfa_resolves_foreign_keys_cleanly(client, phase3_db):
    """Prueba Crítica: elimina usuario con 2FA activo y registros vinculados sin IntegrityError."""
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin.phase3@ucundinamarca.edu.co", "password": "AdminSecurePassword123"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    # Activar 2FA para el usuario analista
    user_login = client.post("/api/v1/auth/login", json={"email": "analyst.phase3@ucundinamarca.edu.co", "password": "AnalystPassword123"}).json()
    user_headers = {"Authorization": f"Bearer {user_login['access_token']}"}
    setup = client.post("/api/v1/auth/mfa/setup", headers=user_headers).json()
    code = pyotp.TOTP(setup["secret"]).now()
    verify_res = client.post("/api/v1/auth/mfa/verify", headers=user_headers, json={"code": code})
    assert verify_res.status_code == 200

    target = phase3_db.query(User).filter(User.email == "analyst.phase3@ucundinamarca.edu.co").first()
    assert target.is_mfa_enabled is True
    # Agregar registro en blacklist vinculado al usuario
    bl = BlacklistEntry(
        ip="198.51.100.22", ip_type="IPv4", country="CO", threat_score=85,
        category="Botnet", status="Bloqueada", blocked_by_user_id=target.id,
    )
    phase3_db.add(bl)
    phase3_db.commit()

    # Eliminación administrativa vía DELETE /api/v1/admin/users/{id}
    del_res = client.delete(f"/api/v1/admin/users/{target.id}", headers=admin_headers)
    assert del_res.status_code == 200

    # Comprobar que el usuario ya no existe y no hubo IntegrityError
    assert phase3_db.query(User).filter(User.id == target.id).first() is None
    assert phase3_db.query(MFABackupCode).filter(MFABackupCode.user_id == target.id).count() == 0
    phase3_db.refresh(bl)
    assert bl.blocked_by_user_id is None


def test_admin_mfa_reset_and_audit_logs_endpoints(client, phase3_db):
    """Verifica endpoint administrativo de reset de 2FA y consulta de audit logs."""
    admin_login = client.post("/api/v1/auth/login", json={"email": "admin.phase3@ucundinamarca.edu.co", "password": "AdminSecurePassword123"}).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    target = phase3_db.query(User).filter(User.email == "analyst.phase3@ucundinamarca.edu.co").first()
    target.is_mfa_enabled = True
    target.totp_secret = "TESTSECRET"
    phase3_db.add(MFABackupCode(user_id=target.id, code_hash="dummyhash"))
    phase3_db.commit()

    # Reset de MFA
    reset_res = client.post(f"/api/v1/admin/users/{target.id}/mfa/reset", headers=admin_headers)
    assert reset_res.status_code == 200
    phase3_db.refresh(target)
    assert target.is_mfa_enabled is False
    assert target.totp_secret is None
    assert phase3_db.query(MFABackupCode).filter(MFABackupCode.user_id == target.id).count() == 0

    # Consulta de Audit Logs
    logs_res = client.get("/api/v1/admin/audit-logs?limit=50", headers=admin_headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) > 0
    actions = [log["action"] for log in logs]
    assert "ADMIN_MFA_RESET" in actions
