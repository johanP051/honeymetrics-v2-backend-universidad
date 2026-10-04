import logging
import os
import random
from datetime import date, datetime, timedelta, timezone
from typing import Generator, List, Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.log_export_model import LogExport
from app.schemas.log_export_schema import (
    LogExportItemResponse,
    LogExportResponse,
    LogReportStatsResponse,
)
from app.services.telegram_service import TelegramService
from app.services.retention_service import RetentionService

logger = logging.getLogger(__name__)


class LogsService:
    """
    Service Layer Pattern: Gestión de solicitudes de extracción de logs crudos,
    persistencia en Base de Datos, almacenamiento particionado en dos capas
    y streaming de datasets reales para Ciencia de Datos y Auditoría CTI.
    """

    # Directorio primario donde residen los archivos particionados locales
    LOCAL_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/downloads"))

    # Fuentes candidatas de datasets históricos consolidados en el host
    DATASET_CANDIDATE_PATHS = [
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/recent_months/logs_2026.08.jsonl",
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/recent_months/logs_2026.07.jsonl",
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/recent_months/logs_2026.06.jsonl",
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/logs_17.jsonl",
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/logs_10003.jsonl",
        "/media/sebas/Exdrive/Workspace/HoneyMetrics/core/media/downloads/logs_1.jsonl",
    ]

    INITIAL_SEEDS = [
        {
            "id": "EXP-1045",
            "start_date": date(2026, 8, 19),
            "end_date": date(2026, 8, 20),
            "date_range": "2026-08-19 / 2026-08-20",
            "count": 21660,
            "status": "Listo",
            "file_format": "JSONL",
            "created_at": datetime(2026, 8, 20, 11, 34, tzinfo=timezone.utc),
        },
        {
            "id": "EXP-1044",
            "start_date": date(2026, 8, 1),
            "end_date": date(2026, 8, 25),
            "date_range": "2026-08-01 / 2026-08-25",
            "count": 112450,
            "status": "Pendiente de Aprobación",
            "file_format": "JSONL",
            "created_at": datetime(2026, 8, 25, 9, 15, tzinfo=timezone.utc),
        },
        {
            "id": "EXP-1043",
            "start_date": date(2026, 8, 16),
            "end_date": date(2026, 8, 16),
            "date_range": "2026-08-16 / 2026-08-16",
            "count": 840,
            "status": "Procesando",
            "file_format": "JSONL",
            "created_at": datetime(2026, 8, 16, 16, 21, tzinfo=timezone.utc),
        },
        {
            "id": "EXP-1042",
            "start_date": date(2026, 7, 1),
            "end_date": date(2026, 7, 31),
            "date_range": "2026-07-01 / 2026-07-31",
            "count": 145200,
            "status": "Rechazada",
            "file_format": "JSONL",
            "created_at": datetime(2026, 7, 31, 14, 0, tzinfo=timezone.utc),
        },
    ]

    @classmethod
    def _format_datetime(cls, dt: datetime) -> str:
        """Formatea un datetime para presentación amigable y consistente."""
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        mes = meses[dt.month - 1]
        hora_12 = dt.hour % 12 or 12
        ampm = "a.m." if dt.hour < 12 else "p.m."
        return f"{dt.day} de {mes} de {dt.year}, {hora_12}:{dt.minute:02d} {ampm}"

    @classmethod
    def seed_initial_data_if_needed(cls, db: Session):
        """Inicializa los datos semilla si la tabla log_exports está vacía."""
        count = db.query(LogExport).count()
        if count == 0:
            for seed in cls.INITIAL_SEEDS:
                export_item = LogExport(
                    id=seed["id"],
                    start_date=seed["start_date"],
                    end_date=seed["end_date"],
                    date_range=seed["date_range"],
                    count=seed["count"],
                    status=seed["status"],
                    file_format=seed["file_format"],
                    created_at=seed["created_at"],
                    updated_at=seed["created_at"],
                )
                db.add(export_item)
            db.commit()

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
        export_id = f"EXP-{random.randint(1000, 9999)}"
        date_range = f"{start_date} / {end_date}"

        # Saneamiento de retención en background para evitar saturación de disco
        if background_tasks:
            background_tasks.add_task(RetentionService.cleanup_old_logs, cls.LOCAL_STORAGE_DIR, 30)

        # Usar WazuhExtractor para count
        real_count = await WazuhExtractor.count_events_for_range(start_date, end_date)

        # Regla de negocio: > 7 días se considera extracción masiva (>50,000 logs)
        if diff_days > 7:
            count = real_count
            status_val = "Pendiente de Aprobación"
            message = "Solicitud masiva enviada a Telegram para aprobación del Administrador."

            if db:
                cls.seed_initial_data_if_needed(db)
                export_record = LogExport(
                    id=export_id,
                    start_date=start_date,
                    end_date=end_date,
                    date_range=date_range,
                    count=count,
                    status=status_val,
                    file_format="JSONL",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(export_record)
                db.commit()

            # Notificación a Telegram (Fail-safe: si falla la red, no aborta la transacción)
            try:
                sent = await TelegramService.send_approval_request(
                    export_id=export_id,
                    count=count,
                    date_range=date_range,
                )
                if not sent:
                    logger.warning("No se pudo notificar a Telegram para export %s", export_id)
            except Exception as e:
                logger.error("Error al notificar a Telegram: %s", str(e))

            return LogExportResponse(
                id=export_id,
                status=status_val,
                count=count,
                message=message,
            )
        else:
            count = real_count
            status_val = "Procesando"
            message = "Solicitud enviada a la cola de extracción asíncrona."

            if db:
                cls.seed_initial_data_if_needed(db)
                export_record = LogExport(
                    id=export_id,
                    start_date=start_date,
                    end_date=end_date,
                    date_range=date_range,
                    count=count,
                    status=status_val,
                    file_format="JSONL",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(export_record)
                db.commit()

                if background_tasks:
                    background_tasks.add_task(cls.extract_and_store_logs_task, export_id, start_date, end_date)

            return LogExportResponse(
                id=export_id,
                status=status_val,
                count=count,
                message=message,
            )

    @classmethod
    def get_history(cls, db: Session) -> List[LogExportItemResponse]:
        """Obtiene el historial completo ordenado por fecha de creación descendente."""
        cls.seed_initial_data_if_needed(db)
        records = db.query(LogExport).order_by(LogExport.created_at.desc()).all()
        return [
            LogExportItemResponse(
                id=rec.id,
                date_range=rec.date_range,
                count=rec.count,
                status=rec.status,
                created_at=cls._format_datetime(rec.created_at),
                file_format=rec.file_format,
            )
            for rec in records
        ]

    @classmethod
    def update_export_status(cls, export_id: str, new_status: str, db: Session) -> bool:
        """Actualiza el estado de una exportación (usado por el webhook de Telegram o worker)."""
        record = db.query(LogExport).filter(LogExport.id == export_id).first()
        if record:
            record.status = new_status
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @classmethod
    def get_export_record(cls, export_id: str, db: Session) -> Optional[LogExport]:
        """Obtiene el registro de exportación por ID."""
        return db.query(LogExport).filter(LogExport.id == export_id).first()

    @classmethod
    async def get_report_stats(cls, export_id: str, db: Session) -> Optional[LogReportStatsResponse]:
        """
        Obtiene las métricas agregadas de decoders y metadatos para la generación del PDF.
        """
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
            labels=labels,
            values=values,
            total_logs=record.count,
            start_date=start_str,
            end_date=end_str,
        )

    @classmethod
    def get_partitioned_files_for_range(cls, start_date: date, end_date: date) -> List[str]:
        """
        Busca en el almacenamiento local los archivos particionados por día
        que caigan dentro del rango [start_date, end_date].
        """
        matched_files = []
        if not os.path.exists(cls.LOCAL_STORAGE_DIR):
            return matched_files

        current = start_date
        while current <= end_date:
            filename = f"logs_{current}.jsonl"
            full_path = os.path.join(cls.LOCAL_STORAGE_DIR, filename)
            if os.path.exists(full_path):
                matched_files.append(full_path)
            current += timedelta(days=1)

        return matched_files

    @classmethod
    def stream_jsonl_dataset(cls, export_id: str, db: Session) -> Generator[bytes, None, None]:
        """
        Generador de streaming HTTP de alto rendimiento para datasets masivos de logs JSONL.
        Estrategia de dos niveles:
        1. Si existen archivos particionados diarios para el rango, transmite sus chunks ordenados.
        2. Si no, busca en los datasets consolidados históricos en el host.
        3. Si no hay archivos, emite un payload sintético estructurado para pruebas en desarrollo.
        """
        record = cls.get_export_record(export_id, db)
        if not record or record.status != "Listo":
            return

        target_count = record.count
        yielded_count = 0

        # Nivel 1: Buscar archivos particionados diarios en data/downloads
        partitioned_files = cls.get_partitioned_files_for_range(record.start_date, record.end_date)
        source_files = partitioned_files if partitioned_files else [p for p in cls.DATASET_CANDIDATE_PATHS if os.path.exists(p)]

        if not source_files:
            # Nivel 3: Fallback sintético defensivo
            yield f'{{"event": "honeymetrics_log", "export_id": "{export_id}", "range": "{record.date_range}", "notice": "Dataset sintetico de desarrollo"}}\n'.encode("utf-8")
            return

        # Nivel 1 y 2: Streaming en bloques sin saturar memoria RAM
        while yielded_count < target_count:
            for source_path in source_files:
                if yielded_count >= target_count:
                    break

                try:
                    with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            clean_line = line.strip()
                            if not clean_line:
                                continue

                            yield (clean_line + "\n").encode("utf-8")
                            yielded_count += 1

                            if yielded_count >= target_count:
                                break
                except Exception as e:
                    logger.warning("Error al leer archivo de logs %s: %s", source_path, str(e))
                    continue

            break

    @classmethod
    async def extract_and_store_logs_task(cls, export_id: str, start_date: date, end_date: date):
        import json
        import asyncio
        from app.db.session import SessionLocal
        from app.services.wazuh_extractor import WazuhExtractor
        
        file_name = f"logs_{start_date}_{end_date}_{export_id}.jsonl"
        os.makedirs(cls.LOCAL_STORAGE_DIR, exist_ok=True)
        file_path = os.path.join(cls.LOCAL_STORAGE_DIR, file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                async for log in WazuhExtractor.extract_logs_scroll(start_date, end_date):
                    f.write(json.dumps(log, ensure_ascii=False) + "\n")
                    
            with SessionLocal() as bg_db:
                cls.update_export_status(export_id, "Listo", bg_db)
        except Exception as e:
            logger.error("Error en extract_and_store_logs_task: %s", str(e))
            with SessionLocal() as bg_db:
                cls.update_export_status(export_id, "Error", bg_db)
                
        cls.garbage_collect_old_logs()

    @classmethod
    def garbage_collect_old_logs(cls):
        import time
        now = time.time()
        if not os.path.exists(cls.LOCAL_STORAGE_DIR):
            return
        for filename in os.listdir(cls.LOCAL_STORAGE_DIR):
            if filename.endswith(".jsonl"):
                filepath = os.path.join(cls.LOCAL_STORAGE_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = now - os.path.getmtime(filepath)
                    if file_age > 72 * 3600:
                        try:
                            os.remove(filepath)
                            logger.info("Garbage collector eliminó archivo antiguo: %s", filepath)
                        except Exception as e:
                            logger.error("Error eliminando archivo %s: %s", filepath, str(e))
