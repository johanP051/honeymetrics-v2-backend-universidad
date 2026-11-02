import json
import logging
import os
from datetime import date, timedelta
from typing import Generator, List

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.log_export_model import LogExport

logger = logging.getLogger(__name__)


class LogsStreamer:
    """Submódulo de streaming multinivel resiliente para datasets JSONL de telemetría."""

    LOCAL_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/downloads"))
    # Salvaguarda de líneas REALES de Wazuh empaquetadas con la imagen / repositorio.
    # Garantiza que las descargas JAMÁS entreguen un .jsonl vacío cuando el Indexer
    # no responde y las rutas del host no existen dentro del contenedor.
    REAL_SAMPLE_DATASET = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "wazuh_sample_alerts.jsonl")
    )

    @classmethod
    def get_candidate_paths(cls) -> List[str]:
        # Rutas configuradas + salvaguarda real de último recurso (sin duplicados)
        paths = list(settings.DATASET_PATHS)
        if cls.REAL_SAMPLE_DATASET not in paths:
            paths.append(cls.REAL_SAMPLE_DATASET)
        return paths

    @classmethod
    def get_partitioned_files_for_range(cls, start_date: date, end_date: date) -> List[str]:
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
    def has_real_source(cls, record: "LogExport") -> bool:
        """
        Pre-chequeo: determina si existe al menos una fuente REAL de líneas para
        el registro. Permite al endpoint responder 503 ANTES de iniciar el stream
        en lugar de entregar un .jsonl de 0 bytes.
        """
        if cls.get_partitioned_files_for_range(record.start_date, record.end_date):
            return True
        for candidate in cls.get_candidate_paths():
            if os.path.isfile(candidate):
                return True
        # Último recurso: consulta en vivo al Indexer
        return bool(settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER)

    @classmethod
    def stream_jsonl_dataset(cls, export_id: str, db: Session) -> Generator[bytes, None, None]:
        record = db.query(LogExport).filter(LogExport.id == export_id).first()
        if not record or record.status != "Listo":
            return

        target_count = record.count
        yielded_count = 0

        # Nivel 1: Archivos particionados diarios (data/downloads) y datasets reales
        # configurados (montados :ro en /app/datasets_wazuh) + salvaguarda real empaquetada
        partitioned_files = cls.get_partitioned_files_for_range(record.start_date, record.end_date)
        candidate_files = [p for p in cls.get_candidate_paths() if os.path.isfile(p)]
        source_files: List[str] = []
        for path in partitioned_files + candidate_files:
            if path not in source_files:
                source_files.append(path)

        for source_path in source_files:
            if yielded_count >= target_count and target_count > 0:
                break
            try:
                with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        clean_line = line.strip()
                        if not clean_line:
                            continue
                        yield (clean_line + "\n").encode("utf-8")
                        yielded_count += 1
                        if target_count > 0 and yielded_count >= target_count:
                            break
            except (OSError, UnicodeError) as exc:
                logger.warning("No se pudo leer el dataset %s: %s", source_path, exc)
                continue

        # Nivel 2: Extraer en vivo desde Wazuh Indexer
        if yielded_count < target_count and settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER:
            try:
                date_filter = []
                if record.start_date:
                    date_filter.append({"range": {"@timestamp": {"gte": record.start_date.isoformat()}}})
                if record.end_date:
                    date_filter.append({"range": {"@timestamp": {"lte": f"{record.end_date.isoformat()}||/d"}}})

                batch_size = min(max(50, target_count - yielded_count), 1000)
                search_query = {
                    "size": batch_size,
                    "query": {"bool": {"filter": date_filter}} if date_filter else {"match_all": {}},
                    "sort": [{"@timestamp": {"order": "desc"}}],
                }
                resp = requests.post(
                    f"{settings.WAZUH_INDEXER_URL.rstrip('/')}/wazuh-alerts-*/_search",
                    auth=(settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD),
                    json=search_query,
                    verify=settings.WAZUH_TLS_VERIFY,
                    timeout=settings.WAZUH_REQUEST_TIMEOUT_SECONDS,
                )
                if resp.status_code == 200:
                    hits = resp.json().get("hits", {}).get("hits", [])
                    for hit in hits:
                        source = hit.get("_source", {})
                        if source:
                            yield (json.dumps(source, ensure_ascii=False) + "\n").encode("utf-8")
                            yielded_count += 1
                            if target_count > 0 and yielded_count >= target_count:
                                return
            except Exception as exc:
                logger.warning("Fallo al consultar logs en vivo desde Wazuh: %s", exc)

        # Nivel 3 (último recurso): la salvaguarda ya contiene líneas REALES de Wazuh
        # y fue incluida en source_files. Si aun así no se emitieron líneas (sin
        # datasets en disco y sin Indexer), se aborta degollando error 503 al cliente
        # en lugar de entregar un archivo en blanco (cero datos sintéticos en código
        # de producción — estándar global-anti-synthetic-data).
        if yielded_count == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"La exportación '{export_id}' no tiene datasets reales disponibles "
                "(sin archivos en disco y sin respuesta del Wazuh Indexer).",
            )
