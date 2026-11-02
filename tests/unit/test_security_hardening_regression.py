"""
Tests de Regresión de Seguridad (Auditoría Caja Blanca Noviembre 2026):
- IPv6 mapeado (::ffff:) y rangos no-globales en la Blacklist (Anti-Bypass SSRF-like)
- Fechas futuras y rango máximo de 365 días en /logs/request-export (Anti-DoS)
- Rate Limiting slowapi en /auth/login y /auth/forgot-password (Anti-Brute-Force)
- Validación de chat_id administrativo en el webhook de Telegram (Anti-Aprobación)
- Política de contraseñas ASVS V2.1 en la creación de usuarios por Admin (12-128)
- Ocultación de /docs y /redoc en producción (Cero Fuga de Información)
- export_id criptográfico con reintentos por colisión
HoneyMetrics Backend v2.0 (UDEC)
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import LogExport
from app.schemas.admin_schema import UserCreateAdminRequest
from app.schemas.log_export_schema import LogExportRequest


# ============================================================
# 1. Validación canónica de red en Blacklist (Anti-Bypass IPv6)
# ============================================================
@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",           # Loopback
        "10.1.2.3",            # RFC1918
        "192.168.1.9",         # RFC1918
        "169.254.10.9",        # Link-local APIPA
        "224.0.0.5",           # Multicast
        "240.0.0.1",           # Reservada Clase E
        "0.0.0.0",             # No especificada
        "::1",                 # Loopback IPv6
        "fe80::1",             # Link-local IPv6
        "fc00::1",             # Unique Local IPv6
        "::ffff:127.0.0.1",    # IPv4-mapeada: loopback disfrazado
        "::ffff:10.0.0.9",     # IPv4-mapeada: RFC1918 disfrazado
        "::ffff:169.254.4.4",  # IPv4-mapeada: link-local disfrazado
        "8.8.8.8",             # DNS público en whitelist interna
        "::ffff:8.8.8.8",      # DNS público en whitelist con IPv6 mapeada
        "::ffff:1.1.1.1",      # DNS público en whitelist con IPv6 mapeada
    ],
)
def test_validate_not_protected_rejects_special_and_mapped_ranges(ip):
    """Las IPs no-globales, whitelist internas y sus versiones ::ffff: deben ser rechazadas con 422."""
    from app.services.blacklist_validation import validate_not_protected

    with pytest.raises(HTTPException):
        validate_not_protected(ip)


def test_validate_not_protected_allows_global_public_ip():
    """Una IP pública y global legítima no debe ser rechazada."""
    from app.services.blacklist_validation import validate_not_protected

    validate_not_protected("1.2.3.4")


# ============================================================
# 2. Guardas de fechas y rango en LogExportRequest (Anti-DoS)
# ============================================================
def test_log_export_request_rejects_future_dates():
    """endDate en el futuro debe rechazarse (no se exportan logs de fechas que aún no ocurren)."""
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        LogExportRequest(startDate=date.today() - timedelta(days=2), endDate=tomorrow)


def test_log_export_request_rejects_reversed_ranges():
    with pytest.raises(ValidationError):
        LogExportRequest(startDate=date.today(), endDate=date.today() - timedelta(days=1))


def test_log_export_request_rejects_ranges_over_365_days():
    """Rangos de más de 365 días deben rechazarse para prevenir overflow/DoS del Indexer."""
    start = date.today() - timedelta(days=400)
    end = date.today() - timedelta(days=10)
    with pytest.raises(ValidationError):
        LogExportRequest(startDate=start, endDate=end)


def test_log_export_request_accepts_valid_one_year_window():
    start = date.today() - timedelta(days=360)
    end = date.today() - timedelta(days=5)
    req = LogExportRequest(startDate=start, endDate=end)
    assert req.start_date == start and req.end_date == end


# ============================================================
# 3. Rate Limiting (slowapi) en credenciales
# ============================================================
@pytest.fixture
def rate_limit_db():
    """SQLite in-memory para que login/forgot-password no golpeen la BD real."""
    from fastapi.testclient import TestClient as _TC  # noqa

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def test_login_rate_limited_after_five_attempts(rate_limit_db):
    """6º intento de login dentro de la ventana debe responder 429."""
    app.dependency_overrides[get_db] = lambda: rate_limit_db
    try:
        client = TestClient(app)
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": f"ratelimit{i}@ucundinamarca.edu.co", "password": "WrongPassword123"},
            ).status_code
            for i in range(6)
        ]
    finally:
        app.dependency_overrides.clear()
    assert all(s in (401, 429) for s in statuses[:5])
    assert statuses[-1] == 429


def test_forgot_password_rate_limited_after_three_attempts(rate_limit_db):
    """4º intento de forgot-password dentro de la ventana debe responder 429."""
    app.dependency_overrides[get_db] = lambda: rate_limit_db
    try:
        client = TestClient(app)
        statuses = [
            client.post(
                "/api/v1/auth/forgot-password",
                json={"email": f"forgot{i}@ucundinamarca.edu.co"},
            ).status_code
            for i in range(4)
        ]
    finally:
        app.dependency_overrides.clear()
    assert all(s == 200 for s in statuses[:3])
    assert statuses[-1] == 429


# ============================================================
# 4. Webhook Telegram: validación estricta de chat_id administrativo
# ============================================================
class _FakeTelegramResponse:
    status_code = 200
    text = "OK"


class _FakeAsyncClient:
    """Sustituto de httpx.AsyncClient para no golpear la API real de Telegram."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, *args, **kwargs):
        return _FakeTelegramResponse()


@pytest.fixture
def web_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(LogExport(
            id="EXP-1001", start_date=date(2026, 1, 1), end_date=date(2026, 1, 5),
            date_range="2026-01-01 / 2026-01-05", count=99999,
            status="Pendiente de Aprobación", file_format="JSONL",
        ))
        session.commit()
        yield session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def web_client(web_db):
    app.dependency_overrides[get_db] = lambda: web_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_telegram_callback_unauthorized_chat_id_cannot_approve(web_client, web_db):
    """Un chat_id distinto del ADMIN_TELEGRAM_CHAT_ID no puede aprobar exportaciones."""
    settings.TELEGRAM_WEBHOOK_SECRET = "audit-secret"
    settings.TELEGRAM_BOT_TOKEN = "123:audit-token"
    settings.ADMIN_TELEGRAM_CHAT_ID = "111222333"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "audit-secret"}
    body = {
        "update_id": 1,
        "callback_query": {
            "id": "cb1",
            "data": "approve_EXP-1001",
            "message": {"message_id": 5, "chat": {"id": 999000111}},
        },
    }
    with patch("app.services.telegram_service.httpx.AsyncClient", _FakeAsyncClient):
        res = web_client.post("/api/v1/logs/webhook/telegram", json=body, headers=headers)

    assert res.status_code == 200
    assert res.json().get("status") == "error"
    web_db.expire_all()
    record = web_db.query(LogExport).filter(LogExport.id == "EXP-1001").first()
    assert record.status == "Pendiente de Aprobación"


def test_telegram_callback_admin_chat_id_approves(web_client, web_db):
    settings.TELEGRAM_WEBHOOK_SECRET = "audit-secret"
    settings.TELEGRAM_BOT_TOKEN = "123:audit-token"
    settings.ADMIN_TELEGRAM_CHAT_ID = "111222333"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "audit-secret"}
    body = {
        "update_id": 1,
        "callback_query": {
            "id": "cb2",
            "data": "approve_EXP-1001",
            "message": {"message_id": 5, "chat": {"id": 111222333}},
        },
    }
    with patch("app.services.telegram_service.httpx.AsyncClient", _FakeAsyncClient):
        res = web_client.post("/api/v1/logs/webhook/telegram", json=body, headers=headers)

    assert res.status_code == 200
    assert res.json().get("status") == "success"
    web_db.expire_all()
    record = web_db.query(LogExport).filter(LogExport.id == "EXP-1001").first()
    assert record.status == "Listo"


def test_telegram_callback_rejected_moves_status_to_rechazada(web_client, web_db):
    settings.TELEGRAM_WEBHOOK_SECRET = "audit-secret"
    settings.TELEGRAM_BOT_TOKEN = "123:audit-token"
    settings.ADMIN_TELEGRAM_CHAT_ID = "111222333"
    headers = {"X-Telegram-Bot-Api-Secret-Token": "audit-secret"}
    body = {
        "update_id": 1,
        "callback_query": {
            "id": "cb3",
            "data": "reject_EXP-1001",
            "message": {"message_id": 5, "chat": {"id": 111222333}},
        },
    }
    with patch("app.services.telegram_service.httpx.AsyncClient", _FakeAsyncClient):
        res = web_client.post("/api/v1/logs/webhook/telegram", json=body, headers=headers)

    assert res.json().get("status") == "success"
    web_db.expire_all()
    record = web_db.query(LogExport).filter(LogExport.id == "EXP-1001").first()
    assert record.status == "Rechazada"


# ============================================================
# 5. Política ASVS V2.1 en creación de usuarios (Admin)
# ============================================================
@pytest.mark.parametrize(
    "weak_password",
    [
        "abc12345",  # 8 chars
        "password1234",        # Denylist ASVS
        "admin12345678",       # Denylist ASVS
        "ShortP@ss" + "0123456789" * 13,  # 139 caracteres: exceden el máximo de 128
    ],
)
def test_admin_temp_password_policy_rejects_weak(weak_password):
    with pytest.raises(ValidationError):
        UserCreateAdminRequest(
            email="new.user@ucundinamarca.edu.co",
            first_names="Nombre", last_names="Apellido",
            role_id=2, temp_password=weak_password,
        )


def test_admin_temp_password_policy_accepts_strong():
    req = UserCreateAdminRequest(
        email="new.user@ucundinamarca.edu.co",
        first_names="Nombre", last_names="Apellido",
        role_id=2, temp_password="TemporalSecure#2026",
    )
    assert req.temp_password == "TemporalSecure#2026"


# ============================================================
# 6. Ocultación de /docs y /redoc en producción
# ============================================================
def _mk_settings(**overrides):
    from app.core.config import Settings

    base = dict(
        _env_file=None,
        ENVIRONMENT="development",
        DEBUG=True,
        SECRET_KEY="unit-test-secret-key",
    )
    base.update(overrides)
    return Settings(**base)


def test_docs_hidden_in_production_with_debug_disabled():
    s = _mk_settings(
        ENVIRONMENT="production", DEBUG=False,
        WAZUH_INDEXER_URL="http://wazuh", WAZUH_INDEXER_USER="u", WAZUH_INDEXER_PASSWORD="p",
    )
    assert s.should_expose_docs() is False


def test_docs_visible_in_development():
    s = _mk_settings()
    assert s.should_expose_docs() is True


def test_production_app_instance_has_no_docs_routes():
    """En producción el objeto FastAPI debe montarse sin /docs ni /redoc."""
    with patch("app.core.config.settings.ENVIRONMENT", "production"), \
         patch("app.core.config.settings.DEBUG", False):
        import importlib
        import asyncio
        import app.main as main_module
        importlib.reload(main_module)
        try:
            assert main_module.app.docs_url is None
            assert main_module.app.redoc_url is None
        finally:
            importlib.reload(main_module)


# ============================================================
# 7. export_id criptográfico con reintentos por colisión
# ============================================================
class _FakeQuery:
    def __init__(self, results):
        # Comparte la cola (sin copiar) para que los pops persistan entre visitas
        self._results = results

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._results.pop(0) if self._results else None


class _FakeDB:
    """Mantiene una única cola de resultados persistente + un counter visual."""

    def __init__(self, results):
        self.results = list(results)
        self.visits = 0

    def query(self, *args, **kwargs):
        self.visits += 1
        return _FakeQuery(self.results)


def test_generate_export_id_retries_on_collision():
    """Si el id ya existe en BD, se debe reintentar con otro valor criptográfico."""
    from app.services.logs_service import LogsService

    fake_db = _FakeDB([object(), None])
    with patch("app.services.logs_service.secrets.randbelow", side_effect=[1233, 5677]) as mock_rand:
        export_id = LogsService._generate_export_id(fake_db)

    assert mock_rand.call_count == 2
    assert fake_db.visits == 2
    assert export_id == "EXP-6677"
    assert export_id.startswith("EXP-")
