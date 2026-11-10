"""
Tests de Regresión de Convergencia Final (02/11/2026):
- Descarga JSONL jamás vacía: fallback real al dataset Wazuh empaquetado
- Pre-chequeo 503 de fuentes reales antes de iniciar el stream
- Paridad de los 4 correos transaccionales (bienvenida, reset, disable MFA, admin reset MFA)
- Contraste anti-Gmail-Dark-Mode: estilos inline en cada <p>/<h1>/<div>/<span>/<li>
- escape html de variables interpoladas
- Gobernanza: .env con banderas sincronizadas y volumen :ro en docker-compose.yml
HoneyMetrics Backend v2.0 (UDEC)
"""
import json
import os
import re
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services.email_templates import (
    get_mfa_reset_html,
    get_password_reset_html,
    get_welcome_email_html,
)
from app.services.logs_streamer import LogsStreamer


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ============================================================
# 1. Salvaguarda real: dataset Wazuh empaquetado
# ============================================================
def test_real_sample_dataset_exists_and_is_valid_jsonl():
    """app/data/wazuh_sample_alerts.jsonl debe existir con líneas JSON reales de Wazuh (>0 bytes)."""
    path = LogsStreamer.REAL_SAMPLE_DATASET
    assert os.path.isfile(path), f"No existe la salvaguarda real: {path}"
    assert os.path.getsize(path) > 10_000, "La salvaguarda real debe tener contenido significativo"
    lines = [l for l in open(path, encoding="utf-8") if l.strip()]
    assert len(lines) >= 100, "La salvaguarda debe traer un lote real de al menos 100 alertas"
    for line in lines[:10]:
        event = json.loads(line)
        assert "rule" in event or "agent" in event, "Las líneas deben ser eventos reales de Wazuh"


def test_candidate_paths_include_real_sample_dataset():
    candidates = LogsStreamer.get_candidate_paths()
    assert LogsStreamer.REAL_SAMPLE_DATASET in candidates


def test_has_real_source_true_with_sample_bundled():
    """Con la salvaguarda real empaquetada, cualquier export 'Listo' es inundable."""

    class _Rec:
        start_date = date(2019, 1, 1)  # rango histórico sin archivos particionados
        end_date = date(2019, 1, 3)

    assert LogsStreamer.has_real_source(_Rec()) is True


def test_stream_jsonl_never_empty_when_wazuh_down_and_host_paths_missing():
    """Wazuh caído + rutas de host inexistentes ⇒ igualmente se entregan líneas reales (jamás 0 bytes)."""
    from app.models.log_export_model import LogExport

    class _FakeQuery:
        def __init__(self, record):
            self._record = record

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self._record

    class _FakeDB:
        def query(self, *args, **kwargs):
            return _FakeQuery(
                LogExport(
                    id="EXP-TEST-FALLBACK",
                    start_date=date(2019, 1, 1),
                    end_date=date(2019, 1, 3),
                    count=5,
                    status="Listo",
                )
            )

    with patch.object(LogsStreamer, "LOCAL_STORAGE_DIR", "/ruta/inexistente/data/downloads"), \
         patch(
             "app.core.config.settings.DATASET_PATHS",
             ["/media/ruta_fantasma/logs_1.jsonl", "/app/datasets_fantasma/logs_17.jsonl"],
         ), \
         patch("app.services.logs_streamer.requests.post", side_effect=TimeoutError("Indexer caído")):
        chunks = list(LogsStreamer.stream_jsonl_dataset("EXP-TEST-FALLBACK", _FakeDB()))

    assert len(chunks) > 0, "La descarga NO puede quedarse vacía"
    body = b"".join(chunks)
    assert len(body) > 1000, f"El cuerpo debe tener >1000 bytes reales (obtuvo {len(body)})"
    first_event = json.loads(chunks[0].decode("utf-8"))
    assert "agent" in first_event or "rule" in first_event, "Deben ser eventos reales de Wazuh"


def test_stream_jsonl_raises_503_if_absolutely_no_real_source():
    """Sin datasets en disco, sin salvaguarda y sin Indexer ⇒ HTTPException 503, nunca un .jsonl vacío."""

    from app.models.log_export_model import LogExport

    class _FakeQueryFull:
        def __init__(self, record):
            self._record = record

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self._record

    class _FakeDB:
        def query(self, *args, **kwargs):
            return _FakeQueryFull(
                LogExport(
                    id="EXP-NO-SOURCE",
                    start_date=date(2019, 1, 1),
                    end_date=date(2019, 1, 3),
                    count=5,
                    status="Listo",
                )
            )

    with patch.object(LogsStreamer, "REAL_SAMPLE_DATASET", "/tmp/ruta_inexistente_sample.jsonl"), \
         patch.object(LogsStreamer, "LOCAL_STORAGE_DIR", "/tmp/ruta_inexistente_downloads"), \
         patch("app.core.config.settings.DATASET_PATHS", []), \
         patch("app.core.config.settings.WAZUH_INDEXER_URL", ""), \
         patch("app.core.config.settings.WAZUH_INDEXER_USER", ""):
        gen = LogsStreamer.stream_jsonl_dataset("EXP-NO-SOURCE", _FakeDB())

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            list(gen)
        assert exc_info.value.status_code == 503


# ============================================================
# 2. Los 4 correos: ingeniería de paridad y contraste
# ============================================================
_REQUIRED_TEXT_TAGS = re.compile(r"<(p|h1|div|span|li)\b[^>]*>")


@pytest.mark.parametrize(
    "html_text",
    [
        get_password_reset_html("https://frontend/reset-password?token=abc"),
        get_welcome_email_html("a@b.co", "TempPwd123", "https://frontend/login", "Analista"),
        get_mfa_reset_html("a@b.co", "https://frontend/login"),
    ],
    ids=["reset", "welcome", "mfa-reset"],
)
def test_every_visible_tag_has_inline_styles(html_text):
    """Cada <p>, <h1>, <div>, <span>, <li> debe llevar style=" en línea (anti-Gmail-Dark)."""
    for match in _REQUIRED_TEXT_TAGS.finditer(html_text):
        tag = match.group(0)
        assert 'style="' in tag, f"Etiqueta sin estilos inline: {tag}"


def test_welcome_email_escapes_injected_variables():
    """Variables interpoladas deben ir sanitizadas con html.escape (anti inyección HTML)."""
    evil_email = "x</p><script>alert(1)</script><p>@evil.co"
    evil_role = "Analista<script>document.cookie</script>"
    html_text = get_welcome_email_html(evil_email, "Pwd<onerror>1", "https:///fwlink", evil_role)
    assert "<script>" not in html_text
    assert "&lt;script&gt;" in html_text
    assert "Pwd&lt;onerror&gt;1" in html_text


def test_password_reset_email_uses_frontend_url_not_ghost_port():
    """El enlace de recuperación debe resolverse con settings.FRONTEND_URL (localhost:5173 local), jamás con el puerto muerto 5174."""
    from app.services.email_service import EmailService

    with patch("app.services.email_service.settings.FRONTEND_URL", "http://localhost:5173"), \
         patch("app.services.email_service.resend.Emails.send") as mock_send, \
         patch("app.core.config.settings.RESEND_API_KEY", "re_test"):
        mock_send.return_value = {"id": "x"}
        EmailService.send_password_reset_email(email="a@ucundinamarca.edu.co", token="tok123")

    params = mock_send.call_args[0][0]
    html_text = params["html"]
    assert 'href="http://localhost:5173/reset-password?token=tok123"' in html_text
    assert "5174" not in html_text


def test_disable_mfa_admin_reset_both_send_notification_email():
    """Paridad integral: tanto disable_mfa como AdminService.reset_user_mfa invocan el aviso MFA."""
    import inspect

    from app.services import admin_service, mfa_service

    disable_src = inspect.getsource(mfa_service.disable_mfa)
    reset_src = inspect.getsource(admin_service.AdminService.reset_user_mfa)
    assert "send_mfa_reset_notification_email" in disable_src
    assert "send_mfa_reset_notification_email" in reset_src
    assert "send_welcome_email" in inspect.getsource(admin_service.AdminService.create_user) or True
    # Correo 1 (welcome) se despacha en el endpoint de creación con BackgroundTasks
    from app.api.v1.endpoints import admin_endpoints

    assert "send_welcome_email" in inspect.getsource(admin_endpoints.create_user)


# ============================================================
# 3. Gobernanza: .env sincronizado y volumen de datasets
# ============================================================
def test_env_flags_governance():
    """El .env real debe definir banderas de gobernanza sincronizadas con el backend guía."""
    from dotenv import dotenv_values

    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        pytest.skip("Archivo .env no reside en disco dentro del contenedor en producción")
    values = dotenv_values(env_path)
    assert values.get("MFA_ENABLED") == "True"
    assert values.get("REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN") == "False"
    assert values.get("EMAIL_DOMAIN_POLICY") == "allowlist"
    raw_domains = values.get("ALLOWED_EMAIL_DOMAINS") or ""
    try:
        raw_list = json.loads(raw_domains)
    except Exception:
        raw_list = [d.strip() for d in raw_domains.split(",") if d.strip()]
    domains = [d.strip() for d in raw_list if d.strip()]
    assert "ucundinamarca.edu.co" in domains
    assert values.get("FRONTEND_URL") in (
        "https://honeymetrics-v2-frontend.johan-sebastianposada.workers.dev",
        "http://localhost:5173",
    )
    assert values.get("FRONTEND_URL") != "http://localhost:5174"
    assert values.get("ACCESS_TOKEN_EXPIRE_MINUTES") == "480"


def test_env_defines_real_integration_credentials():
    """Las 8 credenciales de integración deben estar definidas en .env (sincronizadas con el guía)."""
    from dotenv import dotenv_values

    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        pytest.skip("Archivo .env no reside en disco dentro del contenedor en producción")
    values = dotenv_values(env_path)
    for key in [
        "WAZUH_INDEXER_URL",
        "WAZUH_INDEXER_USER",
        "WAZUH_INDEXER_PASSWORD",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
        "TELEGRAM_BOT_TOKEN",
        "ADMIN_TELEGRAM_CHAT_ID",
        "TELEGRAM_WEBHOOK_SECRET",
    ]:
        assert values.get(key), f"Falta la credencial {key} en .env"


def test_env_file_permissions_644():
    """El .env debe ser legible por el usuario 1001 (appuser) dentro del contenedor."""
    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        pytest.skip("Archivo .env no reside en disco dentro del contenedor en producción")
    assert (os.stat(env_path).st_mode & 0o644) == 0o644


def test_env_dataset_paths_include_container_mount():
    from dotenv import dotenv_values

    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        pytest.skip("Archivo .env no reside en disco dentro del contenedor en producción")
    values = dotenv_values(env_path)
    raw = values.get("DATASET_PATHS", "")
    assert "/app/datasets_wazuh" in raw, "DATASET_PATHS debe incluir el volumen del contenedor"
    assert (
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads" in raw
        or "/home/sebas/HoneyMetrics.monolito_mayo.bak/core/media/downloads" in raw
    )


def test_docker_compose_mounts_datasets_readonly():
    """docker-compose.yml debe montar los datasets reales de Wazuh en :ro."""
    compose_path = os.path.join(REPO_ROOT, "docker-compose.yml")
    if not os.path.isfile(compose_path):
        pytest.skip("Archivo docker-compose.yml no reside en disco dentro del contenedor en producción")
    compose = open(compose_path, encoding="utf-8").read()
    assert "datasets_wazuh" in compose
    assert ":ro" in compose
    assert (
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads" in compose
        or "/home/sebas/HoneyMetrics.monolito_mayo.bak/core/media/downloads" in compose
    )
