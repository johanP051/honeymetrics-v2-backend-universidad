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
