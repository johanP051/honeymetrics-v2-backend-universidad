import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.log_export_model import LogExport
from app.services.logs_streamer import LogsStreamer

logger = logging.getLogger(__name__)


class LogsTasksService:
    """Submódulo de tareas de fondo, seeds y recolección de basura para logs."""

    LOCAL_STORAGE_DIR = LogsStreamer.LOCAL_STORAGE_DIR

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
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        colombia_tz = timezone(timedelta(hours=-5))
        dt_col = dt.astimezone(colombia_tz)
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        mes = meses[dt_col.month - 1]
        hora_12 = dt_col.hour % 12 or 12
        ampm = "a.m." if dt_col.hour < 12 else "p.m."
        return f"{dt_col.day} de {mes} de {dt_col.year}, {hora_12}:{dt_col.minute:02d} {ampm}"

    @classmethod
    def seed_initial_data_if_needed(cls, db: Session):
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
    async def extract_and_store_logs_task(cls, export_id: str, start_date: date, end_date: date):
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
                record = bg_db.query(LogExport).filter(LogExport.id == export_id).first()
                if record:
                    record.status = "Listo"
                    record.updated_at = datetime.now(timezone.utc)
                    bg_db.commit()
        except Exception as e:
            logger.error("Error en extract_and_store_logs_task: %s", str(e))
            with SessionLocal() as bg_db:
                record = bg_db.query(LogExport).filter(LogExport.id == export_id).first()
                if record:
                    record.status = "Error"
                    record.updated_at = datetime.now(timezone.utc)
                    bg_db.commit()

        cls.garbage_collect_old_logs()

    @classmethod
    def garbage_collect_old_logs(cls):
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
                            logger.info("Garbage collector eliminó: %s", filepath)
                        except Exception as e:
                            logger.error("Error eliminando %s: %s", filepath, str(e))
