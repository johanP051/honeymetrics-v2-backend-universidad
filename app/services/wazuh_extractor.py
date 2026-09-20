import json
import logging
import os
from datetime import date, datetime
from typing import Dict, Any, Generator, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WazuhExtractor:
    """
    Servicio de Ingesta Asíncrona desde Wazuh Indexer (OpenSearch).
    Extrae telemetría de eventos crudos mediante Scroll API paginada
    y los consolida en archivos particionados diarios en disco.
    """

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica si las credenciales mínimas de Wazuh están configuradas."""
        return bool(settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER and settings.WAZUH_INDEXER_PASSWORD)

    @classmethod
    async def count_events_for_range(cls, target_date: date) -> int:
        """
        Consulta la cantidad de eventos registrados en Wazuh para una fecha específica.
        """
        if not cls.is_configured():
            return 0

        start_iso = f"{target_date}T00:00:00.000Z"
        end_iso = f"{target_date}T23:59:59.999Z"
        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_count"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}}
                    ],
                    "must_not": [
                        {"terms": {"rule.groups": ["low_diskspace"]}}
                    ]
                }
            }
        }

        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=15.0) as client:
                response = await client.post(url, auth=auth, json=query)
                if response.status_code == 200:
                    return int(response.json().get("count", 0))
        except Exception as e:
            logger.warning("No se pudo conectar a Wazuh Indexer para contar eventos: %s", str(e))
        return 0

    @classmethod
    async def extract_day_to_jsonl(
        cls,
        target_date: date,
        output_dir: str,
        chunk_size: int = 2000,
        max_records: int = 100000,
    ) -> Optional[str]:
        """
        Extrae los eventos de un día específico desde Wazuh Indexer y los guarda
        en formato JSONL: {output_dir}/logs_{target_date}.jsonl.
        Retorna la ruta absoluta del archivo generado o None si falló/no hay conexión.
        """
        if not cls.is_configured():
            logger.info("Wazuh Indexer no está configurado. Omitiendo extracción en vivo.")
            return None

        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"logs_{target_date}.jsonl")

        start_iso = f"{target_date}T00:00:00.000Z"
        end_iso = f"{target_date}T23:59:59.999Z"
        search_url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_search?scroll=2m"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)

        query = {
            "size": chunk_size,
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}}
                    ],
                    "must_not": [
                        {"terms": {"rule.groups": ["low_diskspace"]}}
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}]
        }

        scroll_id = None
        extracted_count = 0

        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=30.0) as client:
                resp = await client.post(search_url, auth=auth, json=query)
                if resp.status_code != 200:
                    logger.warning("Wazuh respondió con error HTTP %d al iniciar scroll.", resp.status_code)
                    return None

                data = resp.json()
                scroll_id = data.get("_scroll_id")
                hits = data.get("hits", {}).get("hits", [])

                with open(file_path, "w", encoding="utf-8") as f:
                    while hits and extracted_count < max_records:
                        for hit in hits:
                            source = hit.get("_source", {})
                            f.write(json.dumps(source, ensure_ascii=False) + "\n")
                            extracted_count += 1
                            if extracted_count >= max_records:
                                break

                        if extracted_count >= max_records:
                            break

                        # Siguiente lote vía Scroll API
                        scroll_url = f"{settings.WAZUH_INDEXER_URL}/_search/scroll"
                        scroll_resp = await client.post(
                            scroll_url,
                            auth=auth,
                            json={"scroll": "2m", "scroll_id": scroll_id}
                        )
                        if scroll_resp.status_code != 200:
                            break
                        scroll_data = scroll_resp.json()
                        scroll_id = scroll_data.get("_scroll_id")
                        hits = scroll_data.get("hits", {}).get("hits", [])

            logger.info("Extracción completada para %s: %d eventos guardados en %s", target_date, extracted_count, file_path)
            return file_path

        except Exception as e:
            logger.error("Error durante la extracción de logs de Wazuh para %s: %s", target_date, str(e))
            return None
        finally:
            if scroll_id:
                try:
                    async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=5.0) as client:
                        await client.request(
                            "DELETE",
                            f"{settings.WAZUH_INDEXER_URL}/_search/scroll",
                            auth=auth,
                            json={"scroll_id": scroll_id},
                        )
                except Exception:
                    pass
