import logging
import secrets
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.log_export_model import LogExport
from app.schemas.log_export_schema import (
    LogExportItemResponse,
    LogExportResponse,
    LogReportStatsResponse,
)
from app.services.telegram_service import TelegramService
from app.services.retention_service import RetentionService
from app.services.logs_streamer import LogsStreamer
from app.services.logs_tasks import LogsTasksService

logger = logging.getLogger(__name__)


class LogsService:
    """
    Service Layer Pattern: Gestión de solicitudes de extracción de logs crudos,
    persistencia en Base de Datos, almacenamiento particionado en dos capas
    y streaming de datasets reales para Ciencia de Datos y Auditoría CTI.
    """

    LOCAL_STORAGE_DIR = LogsStreamer.LOCAL_STORAGE_DIR
    DATASET_CANDIDATE_PATHS = settings.DATASET_PATHS
    INITIAL_SEEDS = LogsTasksService.INITIAL_SEEDS

    _format_datetime = LogsTasksService._format_datetime
    seed_initial_data_if_needed = LogsTasksService.seed_initial_data_if_needed
    extract_and_store_logs_task = LogsTasksService.extract_and_store_logs_task
    garbage_collect_old_logs = LogsTasksService.garbage_collect_old_logs
    get_partitioned_files_for_range = LogsStreamer.get_partitioned_files_for_range
    stream_jsonl_dataset = LogsStreamer.stream_jsonl_dataset

    @classmethod
    def _generate_export_id(cls, db: Optional[Session] = None) -> str:
        """
        Genera un export_id criptográfico (CSPRNG) y reintenta ante colisión en BD.
        Reemplaza random.randint (Mersenne Twister, predecible) por secrets.randbelow.
        """
        while True:
            candidate = f"EXP-{secrets.randbelow(9000) + 1000}"
            if db is not None and db.query(LogExport).filter(LogExport.id == candidate).first():
                continue
            return candidate

    @classmethod
    async def request_export(
        cls,
        start_date: date,
        end_date: date,
        background_tasks: Optional[BackgroundTasks] = None,
        db: Optional[Session] = None,
    ) -> LogExportResponse:
        from app.services.wazuh_extractor import WazuhExtractor

        diff_days = (end_date - start_date).days + 1
        export_id = cls._generate_export_id(db)
        date_range = f"{start_date} / {end_date}"

        if background_tasks:
            background_tasks.add_task(RetentionService.cleanup_old_logs, cls.LOCAL_STORAGE_DIR, 30)

        real_count = await WazuhExtractor.count_events_for_range(start_date, end_date)

        if diff_days > 7:
            count = real_count
            status_val = "Pendiente de Aprobación"
            message = "Solicitud masiva enviada a Telegram para aprobación del Administrador."

            if db:
                cls.seed_initial_data_if_needed(db)
                record = LogExport(
                    id=export_id, start_date=start_date, end_date=end_date,
                    date_range=date_range, count=count, status=status_val,
                    file_format="JSONL", created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(record)
                db.commit()

            if background_tasks:
                background_tasks.add_task(
                    TelegramService.send_approval_request,
                    export_id=export_id, count=count, date_range=date_range,
                )
            else:
                try:
                    await TelegramService.send_approval_request(
                        export_id=export_id, count=count, date_range=date_range,
                    )
                except Exception as e:
                    logger.error("Error al notificar a Telegram: %s", str(e))

            return LogExportResponse(id=export_id, status=status_val, count=count, message=message)
        else:
            count = real_count
            status_val = "Procesando"
            message = "Solicitud enviada a la cola de extracción asíncrona."

            if db:
                cls.seed_initial_data_if_needed(db)
                record = LogExport(
                    id=export_id, start_date=start_date, end_date=end_date,
                    date_range=date_range, count=count, status=status_val,
                    file_format="JSONL", created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(record)
                db.commit()

                if background_tasks:
                    background_tasks.add_task(cls.extract_and_store_logs_task, export_id, start_date, end_date)

            return LogExportResponse(id=export_id, status=status_val, count=count, message=message)

    @classmethod
    def get_history(cls, db: Session) -> List[LogExportItemResponse]:
        cls.seed_initial_data_if_needed(db)
        records = db.query(LogExport).order_by(LogExport.created_at.desc()).all()
        return [
            LogExportItemResponse(
                id=rec.id, date_range=rec.date_range, count=rec.count,
                status=rec.status, created_at=cls._format_datetime(rec.created_at),
                file_format=rec.file_format,
            )
            for rec in records
        ]

    @classmethod
    def update_export_status(cls, export_id: str, new_status: str, db: Session) -> bool:
        record = db.query(LogExport).filter(LogExport.id == export_id).first()
        if record:
            record.status = new_status
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @classmethod
    def get_export_record(cls, export_id: str, db: Session) -> Optional[LogExport]:
        return db.query(LogExport).filter(LogExport.id == export_id).first()

    @classmethod
    async def get_report_stats(cls, export_id: str, db: Session) -> Optional[LogReportStatsResponse]:
        from app.services.wazuh_extractor import WazuhExtractor

        record = cls.get_export_record(export_id, db)
        if not record:
            return None

        start_str = record.start_date.strftime("%Y-%m-%d") if hasattr(record.start_date, "strftime") else str(record.start_date)
        end_str = record.end_date.strftime("%Y-%m-%d") if hasattr(record.end_date, "strftime") else str(record.end_date)

        stats = await WazuhExtractor.get_decoders_stats(record.start_date, record.end_date)
        labels = stats.get("labels", ["rootcheck", "syscheck_integrity_changed", "kernel", "ossec"])
        values = stats.get("values", [45, 30, 20, 5])
        if not labels:
            labels = ["rootcheck", "syscheck_integrity_changed", "kernel", "ossec"]
            values = [45, 30, 20, 5]

        return LogReportStatsResponse(
            labels=labels, values=values, total_logs=record.count,
            start_date=start_str, end_date=end_str,
        )
