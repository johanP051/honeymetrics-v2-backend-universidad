from typing import List
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.log_export_schema import (
    LogExportItemResponse,
    LogExportRequest,
    LogExportResponse,
    LogReportStatsResponse,
)
from app.services.logs_service import LogsService
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/logs", tags=["Logs & Export"])


@router.get(
    "/history",
    response_model=List[LogExportItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener historial persistente de exportaciones de logs",
)
def get_logs_history(db: Session = Depends(get_db)) -> List[LogExportItemResponse]:
    """
    Retorna la lista de todas las exportaciones registradas en base de datos.
    Si la base de datos está vacía, puebla automáticamente los registros de referencia.
    """
    return LogsService.get_history(db)


@router.post(
    "/request-export",
    response_model=LogExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar extracción de logs crudos",
)
async def request_log_export(
    payload: LogExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> LogExportResponse:
    """
    Registra una solicitud de extracción de logs crudos en Base de Datos.
    - Si el rango excede 7 días (>50.000 logs), queda 'Pendiente de Aprobación'
      y envía alerta con inline buttons a Telegram. Retorna HTTP 202 Accepted.
    - Si el rango es menor o igual a 7 días, queda en 'Procesando' y se completa asíncronamente.
    """
    if payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio debe ser anterior o igual a la fecha de fin.",
        )

    return await LogsService.request_export(
        start_date=payload.start_date,
        end_date=payload.end_date,
        background_tasks=background_tasks,
        db=db,
    )


@router.post(
    "/webhook/telegram",
    status_code=status.HTTP_200_OK,
    summary="Webhook de Telegram para aprobaciones interactivas (Inline Buttons)",
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    Recibe las notificaciones de Telegram. Si incluye callback_query (clic en Aprobar/Rechazar),
    procesa la autorización, actualiza el estado en Base de Datos y actualiza el mensaje en el chat.
    """
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token secreto de webhook inválido.",
            )

    body = await request.json()

    if "callback_query" in body:
        result = await TelegramService.handle_callback_query(body["callback_query"])
        if result.get("status") == "success":
            export_id = result.get("export_id")
            action = result.get("action")
            db_status = "Listo" if action == "APROBADA" else "Rechazada"
            LogsService.update_export_status(export_id=export_id, new_status=db_status, db=db)
        return result

    return {"status": "ok"}


@router.get(
    "/download/{export_id}",
    status_code=status.HTTP_200_OK,
    summary="Descargar dataset crudo JSONL de una exportación aprobada",
)
def download_log_export(
    export_id: str,
    db: Session = Depends(get_db),
):
    """
    Descarga por streaming el archivo JSONL para una exportación en estado 'Listo'.
    Transmite los eventos crudos reales sin saturar la memoria RAM del servidor.
    """
    record = LogsService.get_export_record(export_id, db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La exportación '{export_id}' no existe.",
        )

    if record.status != "Listo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La exportación '{export_id}' se encuentra en estado '{record.status}'. Debe estar 'Listo' para su descarga.",
        )

    filename = f"honeymetrics_{export_id}.jsonl"
    generator = LogsService.stream_jsonl_dataset(export_id=export_id, db=db)

    return StreamingResponse(
        content=generator,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Retention-Days": "7",
        },
    )


@router.get(
    "/report-stats/{export_id}",
    response_model=LogReportStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener estadísticas y agregaciones de decoders para reporte PDF",
)
def get_report_stats(
    export_id: str,
    db: Session = Depends(get_db),
) -> LogReportStatsResponse:
    """
    Retorna métricas agregadas por decoders de Wazuh para esquematizar el reporte técnico.
    """
    stats = LogsService.get_report_stats(export_id=export_id, db=db)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La exportación '{export_id}' no existe.",
        )
    return stats
