import pytest
from datetime import date
from unittest.mock import patch
from app.services.logs_service import LogsService


@pytest.mark.anyio
async def test_request_export_massive():
    start = date(2026, 8, 1)
    end = date(2026, 8, 10)

    with patch("app.services.wazuh_extractor.WazuhExtractor.count_events_for_range") as mock_count:
        mock_count.return_value = 100000

        with patch("app.services.telegram_service.TelegramService.send_approval_request") as mock_telegram:
            mock_telegram.return_value = True

            response = await LogsService.request_export(start, end)

            assert response.status == "Pendiente de Aprobación"
            assert response.count == 100000


@pytest.mark.anyio
async def test_request_export_normal():
    start = date(2026, 8, 1)
    end = date(2026, 8, 2)

    with patch("app.services.wazuh_extractor.WazuhExtractor.count_events_for_range") as mock_count:
        mock_count.return_value = 5000

        response = await LogsService.request_export(start, end)

        assert response.status == "Procesando"
        assert response.count == 5000


def test_telegram_webhook_unconfigured_returns_503():
    """Verifica que el webhook falle cerrado con 503 si TELEGRAM_WEBHOOK_SECRET no está configurado."""
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", ""):
        client = TestClient(app)
        response = client.post("/api/v1/logs/webhook/telegram", json={"update_id": 1})
        assert response.status_code == 503
        assert "no configurado" in response.json()["detail"]


def test_telegram_webhook_invalid_secret_token_returns_403():
    """Verifica que el webhook rechace tokens inválidos o faltantes con 403."""
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "super-secret"):
        client = TestClient(app)
        # Sin header
        res_no_header = client.post("/api/v1/logs/webhook/telegram", json={"update_id": 1})
        assert res_no_header.status_code == 403
        assert "inválido" in res_no_header.json()["detail"]

        # Con header incorrecto
        res_wrong = client.post(
            "/api/v1/logs/webhook/telegram",
            headers={"x-telegram-bot-api-secret-token": "wrong-secret"},
            json={"update_id": 1},
        )
        assert res_wrong.status_code == 403
        assert "inválido" in res_wrong.json()["detail"]


def test_telegram_webhook_valid_token_returns_200():
    """Verifica que con token secreto válido el webhook responda 200 OK."""
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "super-secret"):
        client = TestClient(app)
        response = client.post(
            "/api/v1/logs/webhook/telegram",
            headers={"x-telegram-bot-api-secret-token": "super-secret"},
            json={"message": {"text": "ping"}},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_get_report_stats_success():
    """Verifica que /report-stats/{export_id} retorne las agregaciones esperadas."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.db.base import Base
    from app.db.session import get_db
    from app.models.log_export_model import LogExport
    from app.models import Role, User
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from datetime import date

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with Session(engine) as session:
            admin_role = Role(id=1, name="admin", description="Administrador")
            session.add(admin_role)
            user = User(id=1, email="test@example.com", first_names="Test", last_names="User", hashed_password="hash", is_active=True, role_id=1)
            session.add(user)
            exp = LogExport(
                id="EXP-1001",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 2),
                date_range="2026-08-01 / 2026-08-02",
                count=100,
                status="Listo",
            )
            session.add(exp)
            session.commit()

        token = create_access_token(1)
        client = TestClient(app)
        res = client.get("/api/v1/logs/report-stats/EXP-1001", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "labels" in data
        assert "values" in data
        assert data["total_logs"] == 100

        # Test 404 para ID inexistente
        res_404 = client.get("/api/v1/logs/report-stats/EXP-NONEXISTENT", headers={"Authorization": f"Bearer {token}"})
        assert res_404.status_code == 404
        assert "no existe" in res_404.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


