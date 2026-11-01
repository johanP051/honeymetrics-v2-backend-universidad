"""
Tests de Integración y Seguridad para Fase 2: MFA, Backup Codes, Guardas Zero-Trust y PBAC.
HoneyMetrics Backend v2.0 (UDEC)
"""
import pyotp
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.permissions import get_scopes_for_role
from app.core.security import decode_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role, User


@pytest.fixture
def phase2_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        role = Role(name="Administrador", description="Admin general")
        user = User(
            email="phase2@ucundinamarca.edu.co",
            first_names="Sec",
            last_names="Admin",
            hashed_password=hash_password("Testing123456"),
            role=role,
            is_active=True,
            must_change_password=False,
            auth_version=0,
        )
        session.add_all([role, user])
        session.commit()
        session.refresh(user)
        yield session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(phase2_db):
    app.dependency_overrides[get_db] = lambda: phase2_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_mfa_verify_login_emits_full_scopes_and_auth_version(client, phase2_db):
    """Verifica que /auth/mfa/verify-login emita un JWT con scopes del rol y auth_version."""
    login_resp = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()
    token = login_resp["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"}).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/api/v1/auth/mfa/verify", headers={"Authorization": f"Bearer {token}"}, json={"code": code})

    # Segundo login exige 2FA y retorna mfa_token
    mfa_init = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()
    assert mfa_init["mfa_required"] is True

    otp_now = pyotp.TOTP(setup["secret"]).now()
    res = client.post("/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_init["mfa_token"], "code": otp_now})
    assert res.status_code == 200
    data = res.json()
    assert "admin:all" in data["scopes"]
    assert "threats:read" in data["scopes"]
    assert data["user"]["role_name"] == "Administrador"

    payload = decode_access_token(data["access_token"])
    assert "admin:all" in payload["scopes"]
    assert payload["auth_version"] >= 1


def test_mfa_activation_returns_8_backup_codes_and_single_use(client, phase2_db):
    """Verifica que la activación devuelva 8 códigos de respaldo y su consumo de un solo uso."""
    token = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()["access_token"]
    setup = client.post("/api/v1/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"}).json()
    code = pyotp.TOTP(setup["secret"]).now()
    verify_res = client.post("/api/v1/auth/mfa/verify", headers={"Authorization": f"Bearer {token}"}, json={"code": code})
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    backup_codes = vdata["backup_codes"]
    assert len(backup_codes) == 8
    for bc in backup_codes:
        assert len(bc) == 9 and "-" in bc

    # Primer uso del código de respaldo
    mfa_init = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()
    first_res = client.post("/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_init["mfa_token"], "code": backup_codes[0]})
    assert first_res.status_code == 200
    assert "access_token" in first_res.json()

    # Segundo uso del MISMO código debe ser rechazado
    mfa_init2 = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()
    second_res = client.post("/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_init2["mfa_token"], "code": backup_codes[0]})
    assert second_res.status_code == 401


def test_mfa_token_rejected_in_private_endpoints_and_no_replay(client, phase2_db):
    """Verifica que el mfa_token no sirva en endpoints privados y que su jti no sea reutilizable."""
    user = phase2_db.query(User).filter(User.email == "phase2@ucundinamarca.edu.co").first()
    user.is_mfa_enabled = True
    user.totp_secret = "JBSWY3DPEHPK3PXP"
    phase2_db.commit()

    mfa_init = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()
    mfa_token = mfa_init["mfa_token"]

    # Rechazo 401 en endpoints privados
    priv = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {mfa_token}"})
    assert priv.status_code == 401

    otp = pyotp.TOTP("JBSWY3DPEHPK3PXP").now()
    ok_res = client.post("/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_token, "code": otp})
    assert ok_res.status_code == 200

    # Intento de reusar el mismo mfa_token debe fallar por anti-replay
    replay_res = client.post("/api/v1/auth/mfa/verify-login", json={"mfa_token": mfa_token, "code": otp})
    assert replay_res.status_code == 401


def test_must_change_password_server_side_caging(client, phase2_db):
    """Verifica confinamiento de usuarios con must_change_password=True en endpoints operativos."""
    user = phase2_db.query(User).filter(User.email == "phase2@ucundinamarca.edu.co").first()
    user.must_change_password = True
    phase2_db.commit()

    token = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()["access_token"]
    # Endpoint operativo denegado con 403
    op_res = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert op_res.status_code == 403
    assert "temporal" in op_res.json()["detail"].lower()

    # Endpoint permitido (logout)
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200


def test_canonical_role_equivalences_and_anti_spoofing():
    """Verifica equivalencias canónicas exactas y rechazo de nombres parciales inseguros."""
    assert "admin:all" in get_scopes_for_role("Superusuario")
    assert "admin:all" in get_scopes_for_role("Administrador")
    assert "admin:all" in get_scopes_for_role("admin")
    assert "dashboard:read" in get_scopes_for_role("Directivo de T.I.")
    assert "blacklist:read" in get_scopes_for_role("Analista de datos")
    assert "admin:all" not in get_scopes_for_role("No-Admin")
    assert get_scopes_for_role("No-Admin") == []


def test_auth_version_invalidation_rejects_stale_jwt(client, phase2_db):
    """Verifica que incrementar auth_version invalide inmediatamente JWTs anteriores."""
    token = client.post("/api/v1/auth/login", json={"email": "phase2@ucundinamarca.edu.co", "password": "Testing123456"}).json()["access_token"]
    assert client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    user = phase2_db.query(User).filter(User.email == "phase2@ucundinamarca.edu.co").first()
    user.auth_version = user.auth_version + 1
    phase2_db.commit()

    assert client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}).status_code == 401
