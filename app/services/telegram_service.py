import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Servicio de integración con Telegram Bot API para alertas críticas
    y aprobación humana de operaciones masivas (Human-in-the-loop).
    """

    @classmethod
    async def send_approval_request(cls, export_id: str, count: int, date_range: str) -> bool:
        """
        Envía un mensaje interactivo con Inline Keyboard al administrador en Telegram.
        """
        if not settings.TELEGRAM_BOT_TOKEN or not settings.ADMIN_TELEGRAM_CHAT_ID:
            logger.warning(
                "Telegram no configurado (TELEGRAM_BOT_TOKEN o ADMIN_TELEGRAM_CHAT_ID vacíos). "
                "Omitiendo notificación al bot."
            )
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        text = (
            f"🚨 *ALERTA DE EXTRACCIÓN MASIVA*\n\n"
            f"Se han solicitado *{count:,} logs* para el rango `{date_range}`\\.\n"
            f"Id: `{export_id}`\n\n"
            f"¿Desea autorizar esta operación intensiva?"
        )

        payload = {
            "chat_id": settings.ADMIN_TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "MarkdownV2",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "✅ Aprobar", "callback_data": f"approve_{export_id}"},
                        {"text": "❌ Rechazar", "callback_data": f"reject_{export_id}"},
                    ]
                ]
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info(
                        "Notificación de Telegram enviada exitosamente para export %s",
                        export_id,
                    )
                    return True
                else:
                    logger.error(
                        "Error al enviar mensaje a Telegram: HTTP %d - %s",
                        response.status_code,
                        response.text,
                    )
                    return False
        except Exception as e:
            logger.error("Excepción al conectar con la API de Telegram: %s", str(e))
            return False

    @classmethod
    async def handle_callback_query(cls, callback_query: dict) -> dict:
        """
        Procesa el clic de un botón interactivo (Inline Keyboard) desde Telegram,
        notifica al usuario con answerCallbackQuery y actualiza el mensaje original.
        """
        callback_id = callback_query.get("id")
        data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")

        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            return {"status": "error", "detail": "Token no configurado"}

        # Identificar la acción y el export_id
        if data.startswith("approve_"):
            export_id = data.replace("approve_", "")
            action = "APROBADA"
            emoji = "✅"
            feedback = f"¡Solicitud {export_id} autorizada con éxito!"
        elif data.startswith("reject_"):
            export_id = data.replace("reject_", "")
            action = "RECHAZADA"
            emoji = "❌"
            feedback = f"Solicitud {export_id} cancelada."
        else:
            return {"status": "ignored"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Responder al callback para quitar el spinner en la app de Telegram
            answer_url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
            await client.post(
                answer_url,
                json={
                    "callback_query_id": callback_id,
                    "text": feedback,
                    "show_alert": False,
                },
            )

            # 2. Actualizar el texto del mensaje original y remover los botones
            if message_id and chat_id:
                edit_url = f"https://api.telegram.org/bot{token}/editMessageText"
                new_text = (
                    f"{emoji} *SOLICITUD {action}*\n\n"
                    f"La exportación masiva `{export_id}` ha sido *{action.lower()}* por el Administrador\\.\n"
                    f"Estado: `{'Aprobada y Lista para Descarga' if action == 'APROBADA' else 'Cancelada por Administrador'}`"
                )
                await client.post(
                    edit_url,
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": new_text,
                        "parse_mode": "MarkdownV2",
                        "reply_markup": {"inline_keyboard": []},  # Elimina los botones
                    },
                )

        logger.info("Callback Telegram procesado para export %s: %s", export_id, action)
        return {"status": "success", "export_id": export_id, "action": action}
