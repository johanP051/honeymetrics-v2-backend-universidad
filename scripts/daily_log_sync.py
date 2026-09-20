"""
Script de sincronización diaria y rotación de retención para HoneyMetrics v2.
Diseñado para ejecutarse mediante cronjob a las 00:05 AM:
docker compose exec api python -m scripts.daily_log_sync
"""

import asyncio
import logging
from datetime import date, timedelta
from app.services.wazuh_extractor import WazuhExtractor
from app.services.retention_service import RetentionService
from app.services.logs_service import LogsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("daily_log_sync")


async def main():
    logger.info("=== Iniciando Tarea Programada de Sincronización y Retención ===")

    # 1. Purgar archivos mayores a 30 días para preservar el disco
    storage_dir = LogsService.LOCAL_STORAGE_DIR
    purged = RetentionService.cleanup_old_logs(storage_dir=storage_dir, max_days=30)
    logger.info("Fase 1 completada: %d archivos antiguos purgados.", purged)

    # 2. Extraer el consolidado del día de ayer
    yesterday = date.today() - timedelta(days=1)
    logger.info("Fase 2: Extrayendo eventos de Wazuh para el día consolidado: %s...", yesterday)

    if WazuhExtractor.is_configured():
        output_file = await WazuhExtractor.extract_day_to_jsonl(
            target_date=yesterday,
            output_dir=storage_dir,
            chunk_size=2000,
            max_records=100000,
        )
        if output_file:
            logger.info("Extracción exitosa guardada en: %s", output_file)
        else:
            logger.warning("No se pudieron extraer eventos de Wazuh para %s (posiblemente sin conexión).", yesterday)
    else:
        logger.info("Wazuh Indexer no está configurado en este entorno. Omitiendo extracción en caliente.")

    logger.info("=== Tarea Programada de Ingesta Finalizada ===")


if __name__ == "__main__":
    asyncio.run(main())
