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
    role = Role(
        name="admin",
        description="Adminsitrador",
    )

    user = User(
        email="admin@example.com",
        first_names="Administrador",
        last_names="Prueba",
        hashed_password=hash_password("Testing123"),
        role=role,
        is_active=True,
        must_change_password=False,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user) # Despues de esto se deberia crear el identificador

    # Entrega el user al test que lo solicite
    return user

# Probar preparacion de datos
def test_active_user_is_created(db_session, active_user):
    assert active_user.id is not None
    assert active_user.email == "admin@example.com"
    assert active_user.role.name == "admin"

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()

def test_login_with_valid_credentials(client, active_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": active_user.email,
            "password": "Testing123"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"]

def test_login_with_invalid_email(client, active_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "correo-invalido.com",
            "password": "Testing123",
        }
    )

    assert response.status_code == 422