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
                    <div style="text-align: center; margin-bottom: 24px;">
                        <img src="https://honeymetrics-frontend.johan-sebastianposada.workers.dev/assets/HoneyMetrics_logo_circled-CKMXzEJT.png" alt="HoneyMetrics Logo" width="72" height="72" style="display: inline-block; border-radius: 50%; border: 2px solid #d4af37;" />
                    </div>
                    <h1 class="title">Recuperación de Acceso — HoneyMetrics UDEC</h1>
                    <p>Hola,</p>
                    <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta académica en la plataforma HoneyMetrics UDEC.</p>
                    <p>Para definir tu nueva clave de acceso, por favor haz clic en el siguiente enlace de uso único:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Restablecer mi Contraseña</a>
                    </p>
                    <p>Este enlace tiene una vigencia estricta de <strong>1 hora</strong> por motivos de seguridad.</p>
                    <p>Si no realizaste esta solicitud, puedes ignorar este mensaje de forma segura. Tu contraseña actual no será modificada.</p>
                    <div style="margin-top: 24px; padding: 12px; background-color: rgba(255, 255, 255, 0.03); border: 1px dashed #475569; border-radius: 6px; font-size: 11px; color: #94a3b8; text-align: center;">
                        Este es un correo electrónico generado automáticamente por la plataforma HoneyMetrics. Por favor, no respondas a este mensaje ya que esta casilla no es monitoreada.
                    </div>
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

    @staticmethod
    def send_welcome_email(email: str, temp_password: str) -> bool:
        """Envía credenciales temporales de bienvenida a un nuevo usuario creado por el Administrador."""
        try:
            if settings.RESEND_API_KEY:
                resend.api_key = settings.RESEND_API_KEY
            else:
                logger.warning("RESEND_API_KEY no configurada. Envío de bienvenida en simulación.")

            # Blindaje de aislamiento: Evitar enlaces cruzados hacia el frontend del proyecto guía
            is_external_guide = "honeymetrics-frontend.johan-sebastianposada.workers.dev" in (settings.FRONTEND_URL or "")
            if settings.FRONTEND_URL and not is_external_guide and not settings.FRONTEND_URL.startswith("http://localhost"):
                cta_section = f'''
                    <p style="text-align: center;">
                        <a href="{settings.FRONTEND_URL}/login" class="button">Iniciar Sesión en HoneyMetrics UDEC</a>
                    </p>
                '''
            else:
                cta_section = '''
                    <div style="background-color: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 6px; padding: 14px; margin: 20px 0; text-align: center; font-size: 13px; color: #94a3b8;">
                        🔒 <em>La interfaz web de HoneyMetrics UDEC se encuentra en proceso de integración académica. Consérvese esta contraseña temporal para el acceso al portal institucional oficial.</em>
                    </div>
                '''

            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; }}
                    .card {{ background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 32px; max-width: 560px; margin: 0 auto; }}
                    .title {{ color: #d4af37; font-size: 24px; font-weight: bold; margin-bottom: 16px; }}
                    .cred-box {{ background-color: #0f172a; border: 1px dashed #d4af37; border-radius: 6px; padding: 16px; margin: 20px 0; font-family: monospace; }}
                    .alert-box {{ background-color: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; padding: 12px; margin: 16px 0; border-radius: 4px; color: #fbbf24; font-size: 14px; }}
                    .button {{ display: inline-block; background-color: #d4af37; color: #0f172a; padding: 12px 24px; font-weight: bold; text-decoration: none; border-radius: 6px; margin: 24px 0; }}
                    .footer {{ font-size: 12px; color: #94a3b8; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div style="text-align: center; margin-bottom: 24px;">
                        <img src="https://honeymetrics-frontend.johan-sebastianposada.workers.dev/assets/HoneyMetrics_logo_circled-CKMXzEJT.png" alt="HoneyMetrics Logo" width="72" height="72" style="display: inline-block; border-radius: 50%; border: 2px solid #d4af37;" />
                    </div>
                    <h1 class="title">Bienvenido a HoneyMetrics UDEC</h1>
                    <p>Hola,</p>
                    <p>Se ha creado exitosamente tu cuenta de acceso a la plataforma académica de Cyber Threat Intelligence <strong>HoneyMetrics UDEC</strong>.</p>
                    <div class="cred-box">
                        <p style="margin: 4px 0;"><strong>Usuario / Correo:</strong> {email}</p>
                        <p style="margin: 4px 0;"><strong>Contraseña Temporal:</strong> {temp_password}</p>
                    </div>
                    <div class="alert-box">
                        <strong>⚠️ Importante:</strong> Por políticas de seguridad, debes <strong>cambiar tu contraseña</strong> obligatoriamente al realizar tu primer inicio de sesión.
                    </div>
                    {cta_section}
                    <div style="margin-top: 24px; padding: 12px; background-color: rgba(255, 255, 255, 0.03); border: 1px dashed #475569; border-radius: 6px; font-size: 11px; color: #94a3b8; text-align: center;">
                        Este es un correo electrónico generado automáticamente por la plataforma HoneyMetrics. Por favor, no respondas a este mensaje ya que esta casilla no es monitoreada.
                    </div>
                    <div class="footer">
                        <p>HoneyMetrics UDEC &bull; Ingeniería de Software II &bull; Cátedra Universitaria</p>
                    </div>
                </div>
            </body>
            </html>
            """

            params: resend.Emails.SendParams = {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [email],
                "subject": "[UDEC] Credenciales de Acceso — HoneyMetrics",
                "html": html_content,
            }

            if settings.RESEND_API_KEY:
                response = resend.Emails.send(params)
                logger.info(f"Correo de bienvenida UDEC enviado a {email}. ID: {response}")
            else:
                logger.info(f"[SIMULACIÓN-UDEC] Credenciales de bienvenida para {email} con clave: {temp_password}")

            return True
        except Exception as e:
            logger.error(f"Error Resend UDEC bienvenida hacia {email}: {e}", exc_info=True)
            return False

