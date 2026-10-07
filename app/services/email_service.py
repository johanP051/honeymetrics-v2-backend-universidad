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
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; }}
                    .card {{ background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 32px; max-width: 560px; margin: 0 auto; }}
                    .title {{ color: #d4af37; font-size: 24px; font-weight: bold; margin-bottom: 16px; }}
                    .button {{ display: inline-block; background-color: #d4af37; color: #0f172a; padding: 12px 24px; font-weight: bold; text-decoration: none; border-radius: 6px; margin: 24px 0; }}
                    .footer {{ font-size: 12px; color: #94a3b8; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1 class="title">Recuperación de Acceso — HoneyMetrics UDEC</h1>
                    <p>Hola,</p>
                    <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta académica en la plataforma HoneyMetrics UDEC.</p>
                    <p>Para definir tu nueva clave de acceso, por favor haz clic en el siguiente enlace de uso único:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Restablecer mi Contraseña</a>
                    </p>
                    <p>Este enlace tiene una vigencia estricta de <strong>1 hora</strong> por motivos de seguridad.</p>
                    <p>Si no realizaste esta solicitud, puedes ignorar este mensaje de forma segura. Tu contraseña actual no será modificada.</p>
                    <div class="footer">
                        <p>HoneyMetrics UDEC &bull; Ingeniería de Software II</p>
                    </div>
                </div>
            </body>
            </html>
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
