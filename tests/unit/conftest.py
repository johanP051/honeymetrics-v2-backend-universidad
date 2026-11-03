"""
Conftest de la suite unitaria.
Aísla el contador global de slowapi entre tests para que la cuota de un test
no contamine a otro (convención tomada del backend guía honeymetrics-backend).
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter_storage():
    try:
        from app.core.rate_limit import limiter
    except ImportError:
        yield
        return
    # Ventana limpia antes y después de cada test
    limiter._storage.reset()
    yield
    limiter._storage.reset()
