from datetime import date
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.api.deps import get_current_user
from app.services.threat_service import ThreatService
from app.schemas.threat_schema import (
    AttackerIPSchema,
    BotnetSubnetSchema,
    ThreatSummarySchema,
)

from unittest.mock import patch

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated_threat_requests():
    app.dependency_overrides[get_current_user] = lambda: object()
    with patch("app.services.wazuh_extractor.WazuhExtractor.check_connection", return_value=False):
        yield
    app.dependency_overrides.pop(get_current_user, None)


# ==========================================
# Pruebas Unitarias del Servicio (ThreatService)
# ==========================================


def test_threat_score_calculation_bounds():
    """Valida los límites matemáticos del algoritmo de Threat Score (0 a 100)."""
    # Score mínimo
    score_low = ThreatService.calculate_threat_score(
        total_events=10, months_count=0, avg_severity=1.0, tactics_variety=1
    )
    assert 5 <= score_low <= 100

    # Score máximo saturado
    score_high = ThreatService.calculate_threat_score(
        total_events=100000, months_count=5, avg_severity=10.0, tactics_variety=5
    )
    assert score_high == 100


@pytest.mark.anyio
async def test_get_top_persistent_threats_service():
    """Valida que el servicio retorne las amenazas persistentes ordenadas por score descendente."""
    threats = await ThreatService.get_top_persistent_threats()
    assert len(threats) > 0
    assert isinstance(threats[0], AttackerIPSchema)

    # Comprobar orden descendente
    scores = [t.threat_score for t in threats]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_get_detected_botnets_service():
    """Valida la detección de subredes /24 coordinadas."""
    botnets = await ThreatService.get_detected_botnets()
    assert len(botnets) > 0
    assert isinstance(botnets[0], BotnetSubnetSchema)
    assert "/24" in botnets[0].subnet
    assert len(botnets[0].sample_ips) > 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    "preset,expected_events",
    [
        ("24h", 1920),
        ("7d", 28400),
        ("30d", 84200),
        ("90d", 142000),
    ],
)
async def test_threat_summary_presets_service(preset, expected_events):
    """Valida la respuesta del resumen CTI para cada uno de los presets temporales rápidos."""
    summary = await ThreatService.get_threat_summary(range_preset=preset)
    assert isinstance(summary, ThreatSummarySchema)
    assert summary.total_analyzed_events == expected_events
    assert summary.unique_attacker_ips > 0
    assert len(summary.top_attackers) > 0


@pytest.mark.anyio
async def test_threat_summary_custom_dates_out_of_range():
    """Valida que rangos fuera de la ventana de actividad histórica retornen 0 eventos."""
    summary = await ThreatService.get_threat_summary(start_date=date(2025, 1, 1), end_date=date(2025, 1, 15))
    assert summary.total_analyzed_events == 0
    assert summary.unique_attacker_ips == 0
    assert summary.peak_hour_utc == "N/A"
    assert summary.top_attackers == []


@pytest.mark.anyio
async def test_threat_summary_invalid_inverted_dates():
    """Valida que una fecha de inicio posterior al fin lance HTTPException 400."""
    with pytest.raises(HTTPException) as exc_info:
        await ThreatService.get_threat_summary(start_date=date(2026, 8, 30), end_date=date(2026, 8, 1))
    assert exc_info.value.status_code == 400


# ==========================================
# Pruebas de Integración de Endpoints HTTP
# ==========================================


def test_api_health_endpoint():
    """Verifica el endpoint GET /api/v1/threats/health."""
    response = client.get("/api/v1/threats/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "HoneyMetrics" in data["service"]


def test_api_summary_default():
    """Verifica el endpoint GET /api/v1/threats/summary por defecto."""
    response = client.get("/api/v1/threats/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyzed_events"] == 165247
    assert data["unique_attacker_ips"] == 1107
    assert len(data["top_attackers"]) > 0
    assert len(data["detected_botnets"]) > 0


def test_api_summary_with_preset():
    """Verifica GET /api/v1/threats/summary?range=24h."""
    response = client.get("/api/v1/threats/summary?range=24h")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyzed_events"] == 1920
    assert data["peak_hour_utc"] == "14:00 - 15:00 UTC"


def test_api_summary_inverted_dates_returns_400():
    """Verifica que fechas invertidas en query params retornen HTTP 400."""
    response = client.get("/api/v1/threats/summary?start_date=2026-08-30&end_date=2026-08-01")
    assert response.status_code == 400
    assert "start_date" in response.json()["detail"]


def test_api_top_persistent_endpoint():
    """Verifica el endpoint GET /api/v1/threats/top-persistent."""
    response = client.get("/api/v1/threats/top-persistent")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["threat_score"] >= data[-1]["threat_score"]


def test_api_botnets_endpoint():
    """Verifica el endpoint GET /api/v1/threats/botnets."""
    response = client.get("/api/v1/threats/botnets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "/24" in data[0]["subnet"]


@pytest.mark.anyio
async def test_wazuh_extractor_count_events_for_preset():
    """Verifica que WazuhExtractor.count_events_for_preset consulte OpenSearch con query range."""
    from unittest.mock import patch, MagicMock
    from app.services.wazuh_extractor import WazuhExtractor

    with patch.object(WazuhExtractor, "is_configured", return_value=True):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"count": 42000}
            mock_post.return_value = mock_resp

            count = await WazuhExtractor.count_events_for_preset("7d")
            assert count == 42000
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "now-7d" in str(kwargs.get("json"))


@pytest.mark.anyio
async def test_threat_summary_dynamic_wazuh_count_when_online():
    """Verifica que ThreatService actualice total_events dinámicamente si Wazuh está online."""
    from unittest.mock import patch
    from app.services.wazuh_extractor import WazuhExtractor

    with patch.object(WazuhExtractor, "check_connection", return_value=True):
        with patch.object(WazuhExtractor, "count_events_for_preset", return_value=35000):
            summary = await ThreatService.get_threat_summary(range_preset="7d")
            assert summary.total_analyzed_events == 35000

