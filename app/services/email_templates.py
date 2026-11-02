"""
Plantillas HTML de correo transaccional anti-Gmail-Dark-Mode para HoneyMetrics v2 UDEC.
Todos los elementos HTML cuentan con estilos inline explícitos de alto contraste
(#f8fafc / #e2e8f0 sobre #0f172a / #1e293b) para evitar inversión o pérdida de legibilidad.
"""
import html


def get_password_reset_html(reset_url: str) -> str:
    """Plantilla de recuperación de acceso institucional con estilos inline anti-dark-mode."""
    safe_url = html.escape(reset_url)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Recuperación de Contraseña</title></head>
<body style="margin:0;padding:20px;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e2e8f0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0f172a;">
    <tr><td align="center" style="padding:16px;">
      <div style="background-color:#1e293b;border:1px solid #334155;border-radius:8px;padding:32px;max-width:560px;margin:0 auto;text-align:left;">
        <div style="text-align:center;margin-bottom:24px;">
          <img src="cid:honeymetrics_logo" alt="HoneyMetrics_logo_circled" width="72" height="72" style="display:inline-block;border-radius:50%;border:2px solid #d4af37;" />
        </div>
        <h1 style="color:#d4af37;font-size:22px;font-weight:bold;margin:0 0 16px 0;text-align:center;">Recuperación de Acceso — HoneyMetrics</h1>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Hola,</p>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Hemos recibido una solicitud para restablecer la contraseña de tu cuenta institucional en HoneyMetrics.</p>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Para definir una nueva contraseña, haz clic en el siguiente enlace de uso único:</p>
        <p style="text-align:center;margin:28px 0;">
          <a href="{safe_url}" style="display:inline-block;background-color:#d4af37;color:#0f172a!important;padding:12px 28px;font-weight:bold;text-decoration:none;border-radius:6px;font-size:15px;">Restablecer mi Contraseña</a>
        </p>
        <p style="color:#e2e8f0;font-size:14px;line-height:1.5;margin:12px 0;">Este enlace tiene una vigencia estricta de <strong style="color:#f8fafc;">1 hora</strong> por motivos de seguridad.</p>
        <p style="color:#94a3b8;font-size:13px;line-height:1.5;margin:12px 0;">Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura.</p>
        <div style="margin-top:24px;padding:12px;background-color:#0f172a;border:1px dashed #475569;border-radius:6px;font-size:11px;color:#94a3b8;text-align:center;">
          Este es un correo electrónico generado automáticamente por la plataforma HoneyMetrics. Por favor, no respondas a este mensaje ya que esta casilla no es monitoreada.
        </div>
        <div style="margin-top:20px;border-top:1px solid #334155;padding-top:14px;text-align:center;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">HoneyMetrics Security Operations &bull; Universidad de Cundinamarca</p>
        </div>
      </div>
    </td></tr>
  </table>
</body>
</html>"""


def get_welcome_email_html(email: str, temp_password: str, login_url: str, role_name: str = "Usuario") -> str:
    """Plantilla de bienvenida y credenciales temporales con enlace directo al portal."""
    safe_email = html.escape(email)
    safe_pwd = html.escape(temp_password)
    safe_url = html.escape(login_url)
    safe_role = html.escape(role_name)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Bienvenido a HoneyMetrics</title></head>
<body style="margin:0;padding:20px;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e2e8f0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0f172a;">
    <tr><td align="center" style="padding:16px;">
      <div style="background-color:#1e293b;border:1px solid #334155;border-radius:8px;padding:32px;max-width:560px;margin:0 auto;text-align:left;">
        <div style="text-align:center;margin-bottom:24px;">
          <img src="cid:honeymetrics_logo" alt="HoneyMetrics_logo_circled" width="72" height="72" style="display:inline-block;border-radius:50%;border:2px solid #d4af37;" />
        </div>
        <h1 style="color:#d4af37;font-size:22px;font-weight:bold;margin:0 0 16px 0;text-align:center;">Bienvenido a HoneyMetrics CTI</h1>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Hola,</p>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Se ha creado una cuenta institucional para ti con el rol de <strong style="color:#f8fafc;">{safe_role}</strong>.</p>
        <div style="background-color:#0f172a;border:1px dashed #d4af37;border-radius:6px;padding:16px;margin:20px 0;color:#f8fafc;">
          <p style="color:#f8fafc;font-family:monospace;font-size:14px;margin:4px 0;"><strong style="color:#d4af37;">Usuario:</strong> {safe_email}</p>
          <p style="color:#f8fafc;font-family:monospace;font-size:14px;margin:4px 0;"><strong style="color:#d4af37;">Contraseña Temporal:</strong> {safe_pwd}</p>
        </div>
        <div style="background-color:rgba(245,158,11,0.12);border-left:4px solid #f59e0b;padding:12px;margin:18px 0;border-radius:4px;">
          <p style="color:#fbbf24;font-size:13px;line-height:1.5;margin:0;"><strong style="color:#fbbf24;">⚠️ Importante:</strong> Por políticas de seguridad, deberás actualizar tu contraseña al iniciar sesión.</p>
        </div>
        <p style="text-align:center;margin:28px 0;">
          <a href="{safe_url}" style="display:inline-block;background-color:#d4af37;color:#0f172a!important;padding:12px 28px;font-weight:bold;text-decoration:none;border-radius:6px;font-size:15px;">Iniciar Sesión en HoneyMetrics</a>
        </p>
        <div style="margin-top:24px;padding:12px;background-color:#0f172a;border:1px dashed #475569;border-radius:6px;font-size:11px;color:#94a3b8;text-align:center;">
          Este es un correo electrónico generado automáticamente por la plataforma HoneyMetrics. Por favor, no respondas a este mensaje ya que esta casilla no es monitoreada.
        </div>
        <div style="margin-top:20px;border-top:1px solid #334155;padding-top:14px;text-align:center;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">HoneyMetrics Security Operations &bull; Universidad de Cundinamarca</p>
        </div>
      </div>
    </td></tr>
  </table>
</body>
</html>"""


def get_mfa_reset_html(email: str, login_url: str) -> str:
    """Plantilla de aviso administrativo de restablecimiento de 2FA."""
    safe_email = html.escape(email)
    safe_url = html.escape(login_url)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Aviso de Seguridad: Restablecimiento de 2FA</title></head>
<body style="margin:0;padding:20px;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e2e8f0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#0f172a;">
    <tr><td align="center" style="padding:16px;">
      <div style="background-color:#1e293b;border:1px solid #334155;border-radius:8px;padding:32px;max-width:560px;margin:0 auto;text-align:left;">
        <div style="text-align:center;margin-bottom:24px;">
          <img src="cid:honeymetrics_logo" alt="HoneyMetrics_logo_circled" width="72" height="72" style="display:inline-block;border-radius:50%;border:2px solid #d4af37;" />
        </div>
        <h1 style="color:#d4af37;font-size:22px;font-weight:bold;margin:0 0 16px 0;text-align:center;">Aviso de Seguridad: Restablecimiento de 2FA</h1>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Hola,</p>
        <p style="color:#e2e8f0;font-size:15px;line-height:1.6;margin:12px 0;">Te informamos que la autenticación de dos factores (2FA) asociada a tu cuenta <strong style="color:#f8fafc;">{safe_email}</strong> ha sido restablecida por un administrador de seguridad de HoneyMetrics.</p>
        <div style="background-color:rgba(239,68,68,0.12);border-left:4px solid #ef4444;padding:12px;margin:18px 0;border-radius:4px;">
          <p style="color:#fca5a5;font-size:13px;line-height:1.5;margin:0;"><strong style="color:#fca5a5;">⚠️ Atención:</strong> Si no solicitaste este restablecimiento, por favor contacta de inmediato al equipo de Seguridad (SOC).</p>
        </div>
        <p style="color:#e2e8f0;font-size:14px;line-height:1.5;margin:12px 0;">Para proteger tu cuenta, inicia sesión y vincula un nuevo dispositivo autenticador desde la Configuración de Perfil.</p>
        <p style="text-align:center;margin:28px 0;">
          <a href="{safe_url}" style="display:inline-block;background-color:#d4af37;color:#0f172a!important;padding:12px 28px;font-weight:bold;text-decoration:none;border-radius:6px;font-size:15px;">Iniciar Sesión</a>
        </p>
        <div style="margin-top:24px;padding:12px;background-color:#0f172a;border:1px dashed #475569;border-radius:6px;font-size:11px;color:#94a3b8;text-align:center;">
          Este es un correo electrónico generado automáticamente por la plataforma HoneyMetrics. Por favor, no respondas a este mensaje ya que esta casilla no es monitoreada.
        </div>
        <div style="margin-top:20px;border-top:1px solid #334155;padding-top:14px;text-align:center;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">HoneyMetrics Security Operations &bull; Universidad de Cundinamarca</p>
        </div>
      </div>
    </td></tr>
  </table>
</body>
</html>"""
