from fastapi.testclient import TestClient
from app.main import app
from app.services.health_service import HealthService
from app.schemas.health import HealthResponseDto

client = TestClient(app)


def test_health_service_direct():
    """Verifica que HealthService retorna un DTO válido con los campos esperados."""
    dto = HealthService.get_health_status()
    assert isinstance(dto, HealthResponseDto)
    assert dto.status == "online"
    assert dto.uptime_seconds >= 0
    assert dto.version == "2.0.0-academic"


def test_health_endpoint_http():
    """Verifica que el controlador /api/v1/health responde 200 OK y el JSON coincide con el contrato DTO."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert data["version"] == "2.0.0-academic"


def test_root_endpoint():
    """Verifica la respuesta informativa de la raíz /."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data
    assert "health" in data
