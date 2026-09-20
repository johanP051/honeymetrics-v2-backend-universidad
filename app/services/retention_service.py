import os
import re
import logging
from datetime import datetime, date, timedelta, timezone

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Servicio de Gobernanza y Limpieza de Disco (TTL - Time To Live).
    Previene la saturación del almacenamiento eliminando archivos de logs
    particionados que superen la ventana de retención (ej. 30 días).
    """

    LOG_FILENAME_PATTERN = re.compile(r"^logs_(\d{4}-\d{2}-\d{2})\.jsonl$")

    @classmethod
    def cleanup_old_logs(cls, storage_dir: str, max_days: int = 30) -> int:
        """
        Escanea el directorio de descargas y elimina los archivos que tengan
        una fecha anterior a (hoy - max_days).
        Retorna la cantidad de archivos eliminados.
        """
        if not os.path.exists(storage_dir):
            logger.info("Directorio de almacenamiento %s no existe. Omitiendo limpieza.", storage_dir)
            return 0

        cutoff_date = date.today() - timedelta(days=max_days)
        removed_count = 0

        for filename in os.listdir(storage_dir):
            match = cls.LOG_FILENAME_PATTERN.match(filename)
            if not match:
                continue

            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()
                if file_date < cutoff_date:
                    file_path = os.path.join(storage_dir, filename)
                    os.remove(file_path)
                    removed_count += 1
                    logger.info("Archivo de log expirado purgado (TTL %d días): %s", max_days, filename)
            except ValueError:
                continue

        logger.info("Ciclo de retención completado: %d archivos purgados en %s.", removed_count, storage_dir)
        return removed_count
