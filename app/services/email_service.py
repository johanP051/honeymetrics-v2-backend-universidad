"""PB-HM-06.1 Correo transaccional UDEC (patrón guía Resend + johan-d3v.site).

Ente distinto de guía: HoneyMetrics UDEC <udec-auth@johan-d3v.site>.
Sin RESEND_API_KEY -> simulación con log (no rompe flujo, útil CI/profe).
"""

import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_password_reset_email(email: str, token: str) -> bool:
        """Envía enlace de recuperación válido 1h. Retorna True siempre salvo error Resend."""
        try:
            if settings.RESEND_API_KEY:
                resend.api_key = settings.RESEND_API_KEY
            else:
                logger.warning("RESEND_API_KEY no configurada. Correo en simulación.")

            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Recuperación de Acceso — HoneyMetrics UDEC</h2>
                <p>Hemos recibido una solicitud para restablecer tu cuenta académica.</p>
                <p><a href="{reset_url}">Restablecer mi contraseña</a></p>
                <p>Vigencia estricta de <strong>1 hora</strong> y un solo uso.</p>
                <p>Si no la solicitaste, ignora este mensaje.</p>
            </div>
            """

            params: resend.Emails.SendParams = {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [email],
                "subject": "[UDEC] Recuperación de Acceso — HoneyMetrics",
                "html": html_content,
            }

            if settings.RESEND_API_KEY:
                response = resend.Emails.send(params)
                logger.info(f"Correo UDEC enviado a {email}. ID: {response}")
            else:
                logger.info(f"[SIMULACIÓN-UDEC] Reset para {email}: {reset_url}")

            return True
        except Exception as e:
            logger.error(f"Error Resend UDEC hacia {email}: {e}", exc_info=True)
            return False
