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

