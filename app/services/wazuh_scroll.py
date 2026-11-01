import json
import logging
import os
from datetime import date
from typing import AsyncGenerator, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WazuhScrollService:
    """Submódulo de extracción asíncrona masiva vía Scroll API de OpenSearch/Wazuh."""

    @classmethod
    def _is_configured(cls) -> bool:
        return bool(settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER and settings.WAZUH_INDEXER_PASSWORD)

    @classmethod
    async def extract_day_to_jsonl(
        cls,
        target_date: date,
        output_dir: str,
        chunk_size: int = 2000,
        max_records: int = 100000,
    ) -> Optional[str]:
        """Extrae eventos de un día desde Wazuh y los guarda en logs_{target_date}.jsonl."""
        if not cls._is_configured():
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
                    "must": [{"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}}],
                    "must_not": [{"terms": {"rule.groups": ["low_diskspace"]}}],
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
        }

        scroll_id = None
        extracted_count = 0
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=30.0) as client:
                resp = await client.post(search_url, auth=auth, json=query)
                if resp.status_code != 200:
                    logger.warning("Wazuh error HTTP %d al iniciar scroll.", resp.status_code)
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

                        scroll_resp = await client.post(
                            f"{settings.WAZUH_INDEXER_URL}/_search/scroll",
                            auth=auth,
                            json={"scroll": "2m", "scroll_id": scroll_id},
                        )
                        if scroll_resp.status_code != 200:
                            break
                        scroll_data = scroll_resp.json()
                        scroll_id = scroll_data.get("_scroll_id")
                        hits = scroll_data.get("hits", {}).get("hits", [])

            return file_path
        except Exception as e:
            logger.error("Error extrayendo logs Wazuh para %s: %s", target_date, str(e))
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

    @classmethod
    async def extract_logs_scroll(
        cls,
        start_date: date,
        end_date: date,
        chunk_size: int = 5000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generador asíncrono para streaming de logs con Scroll API."""
        if not cls._is_configured():
            return

        start_iso = f"{start_date}T00:00:00.000Z"
        end_iso = f"{end_date}T23:59:59.999Z"
        search_url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_search?scroll=2m"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {
            "size": chunk_size,
            "query": {
                "bool": {
                    "must": [{"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}}],
                    "must_not": [{"terms": {"rule.groups": ["low_diskspace"]}}],
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
        }

        scroll_id = None
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=30.0) as client:
                resp = await client.post(search_url, auth=auth, json=query)
                if resp.status_code != 200:
                    return

                data = resp.json()
                scroll_id = data.get("_scroll_id")
                hits = data.get("hits", {}).get("hits", [])

                while hits:
                    for hit in hits:
                        yield hit.get("_source", {})

                    scroll_resp = await client.post(
                        f"{settings.WAZUH_INDEXER_URL}/_search/scroll",
                        auth=auth,
                        json={"scroll": "2m", "scroll_id": scroll_id},
                    )
                    if scroll_resp.status_code != 200:
                        break
                    scroll_data = scroll_resp.json()
                    scroll_id = scroll_data.get("_scroll_id")
                    hits = scroll_data.get("hits", {}).get("hits", [])
        except Exception as e:
            logger.error("Error en extract_logs_scroll: %s", str(e))
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
