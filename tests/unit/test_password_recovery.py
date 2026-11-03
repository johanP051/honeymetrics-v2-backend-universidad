"""TDD RED - PB-HM-06.1 Recuperación vía correo (guía: Resend + johan-d3v.site).

Criterios:
- Esc1: forgot siempre 200 (anti-enumeración CWE-200), genera token 1h si existe.
- Esc2: reset válido rota clave e invalida token; expirado/reusado -> 400.
Estado: endpoints/servicios aún NO existen -> debe fallar en ROJO.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Role, User
from app.core.security import hash_password

from fastapi.testclient import TestClient


@pytest.fixture
def test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def test_database(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine, test_database):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def active_user(db_session):
    role = Role(name="admin", description="Administrador")
    user = User(
        email="usuario@ucundinamarca.edu.co",
        first_names="Usuario",
        last_names="Prueba",
        hashed_password=hash_password("Testing123"),
        role=role,
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_forgot_password_existing_returns_200(client, active_user):
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": active_user.email},
    )
    assert resp.status_code == 200


def test_forgot_password_unknown_returns_200_anti_enumeration(client):
    resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nadie@ucundinamarca.edu.co"},
    )
    assert resp.status_code == 200


def test_reset_password_invalid_token_returns_400(client):
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalido", "new_password": "NuevaClave123"},
    )
    assert resp.status_code == 400


def test_reset_password_expired_token_returns_400(client, active_user, db_session):
    from datetime import datetime, timedelta, timezone

    forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": active_user.email},
    )
    assert forgot.status_code == 200
    db_session.refresh(active_user)
    assert active_user.reset_token

    active_user.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": active_user.reset_token, "new_password": "NuevaClave123"},
    )
    assert resp.status_code == 400


def test_reset_password_reuse_returns_400(client, active_user, db_session):
    forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": active_user.email},
    )
    assert forgot.status_code == 200
    db_session.refresh(active_user)
    token = active_user.reset_token

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NuevaClave123"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "OtraClave123"},
    )
    assert second.status_code == 400
