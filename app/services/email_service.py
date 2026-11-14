"""
PB-HM-06.1 Correo transaccional UDEC (patrón Resend + anti-Gmail-Dark-Mode).

Maneja envíos defensivos sin romper el flujo HTTP y simulación local cuando
RESEND_API_KEY no se encuentra configurada en el entorno.
"""
import logging
import os
from typing import Any, Dict, List, Optional

import resend

from app.core.config import settings
from app.services.email_templates import (
    get_mfa_reset_html,
    get_password_reset_html,
    get_welcome_email_html,
)

logger = logging.getLogger(__name__)

_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "images", "logo_email.png"
)


def _get_logo_attachments() -> List[Dict[str, Any]]:
    if os.path.exists(_LOGO_PATH):
        try:
            with open(_LOGO_PATH, "rb") as f:
                content = list(f.read())
            return [{
                "filename": "HoneyMetrics_logo_circled.png",
                "content": content,
                "content_id": "honeymetrics_logo"
            }]
        except Exception as e:
            logger.warning(f"No se pudo cargar el adjunto del logo para el correo: {e}")
    return []


def _dispatch_email(to_email: str, subject: str, html_content: str, log_tag: str) -> bool:
    """Helper unificado para despacho de correos vía Resend o simulación con log."""
    try:
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
        else:
            logger.warning(f"RESEND_API_KEY no configurada. Correo [{log_tag}] en simulación.")

        params: resend.Emails.SendParams = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        attachments = _get_logo_attachments()
        if attachments:
            params["attachments"] = attachments

        if settings.RESEND_API_KEY:
            response = resend.Emails.send(params)
            logger.info(f"Correo [{log_tag}] enviado a {to_email}. ID: {response}")
        else:
            logger.info(f"[SIMULACIÓN-{log_tag}] Correo preparado para {to_email}")
        return True
    except Exception as exc:
        logger.error(f"Error Resend [{log_tag}] hacia {to_email}: {exc}", exc_info=True)
        return False


def _build_frontend_url(path: str, base_origin: Optional[str] = None) -> str:
    """Construye una URL absoluta hacia el frontend priorizando base_origin sobre settings.FRONTEND_URL."""
    base = (base_origin or settings.FRONTEND_URL).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


class EmailService:
    @staticmethod
    def send_password_reset_email(
        email: str,
        token: str,
        reset_url: Optional[str] = None,
        base_origin: Optional[str] = None,
    ) -> bool:
        """Envía enlace de recuperación válido 1h. Retorna True siempre salvo error Resend."""
        if not reset_url:
            reset_url = _build_frontend_url(f"reset-password?token={token}", base_origin)
        html_content = get_password_reset_html(reset_url)
        return _dispatch_email(
            to_email=email,
            subject="[UDEC] Recuperación de Acceso — HoneyMetrics",
            html_content=html_content,
            log_tag="PASSWORD_RESET",
        )

    @staticmethod
    def send_welcome_email(
        email: str,
        temp_password: str,
        role_name: str = "Usuario",
        base_origin: Optional[str] = None,
    ) -> bool:
        """Envía credenciales temporales de bienvenida con enlace al login institucional."""
        login_url = _build_frontend_url("login", base_origin)
        html_content = get_welcome_email_html(
            email=email,
            temp_password=temp_password,
            login_url=login_url,
            role_name=role_name,
        )
        return _dispatch_email(
            to_email=email,
            subject="[UDEC] Credenciales de Acceso — HoneyMetrics",
            html_content=html_content,
            log_tag="WELCOME",
        )

    @staticmethod
    def send_user_welcome_email(
        email: str,
        temporary_password: str,
        role_name: str = "Usuario",
        base_origin: Optional[str] = None,
    ) -> bool:
        """Alias para compatibilidad con firmas del backend guía."""
        return EmailService.send_welcome_email(
            email=email,
            temp_password=temporary_password,
            role_name=role_name,
            base_origin=base_origin,
        )

    @staticmethod
    def send_mfa_reset_notification_email(
        email: str,
        base_origin: Optional[str] = None,
    ) -> bool:
        """Notifica al usuario que su 2FA fue reseteado por un administrador institucional."""
        login_url = _build_frontend_url("login", base_origin)
        html_content = get_mfa_reset_html(email=email, login_url=login_url)
        return _dispatch_email(
            to_email=email,
            subject="[UDEC] Aviso de Seguridad: Restablecimiento de 2FA — HoneyMetrics",
            html_content=html_content,
            log_tag="MFA_RESET",
        )
