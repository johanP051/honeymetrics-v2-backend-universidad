import logging
from datetime import date
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WazuhStatsService:
    """Consultas agregadas y conteo de telemetría en Wazuh Indexer."""

    @classmethod
    def _is_configured(cls) -> bool:
        return bool(settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER and settings.WAZUH_INDEXER_PASSWORD)

    @classmethod
    async def count_events_for_range(cls, start_date: date, end_date: date) -> int:
        """Consulta la cantidad de eventos registrados en Wazuh para un rango de fechas."""
        if not cls._is_configured():
            return 0
        start_iso = f"{start_date}T00:00:00.000Z"
        end_iso = f"{end_date}T23:59:59.999Z"
        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_count"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {
            "query": {
                "bool": {
                    "must": [{"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}}],
                    "must_not": [{"terms": {"rule.groups": ["low_diskspace"]}}],
                }
            }
        }
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=4.0) as client:
                resp = await client.post(url, auth=auth, json=query)
                if resp.status_code == 200:
                    return int(resp.json().get("count", 0))
        except Exception as e:
            logger.warning("No se pudo conectar a Wazuh para contar eventos: %s", str(e))
        return 0

    @classmethod
    async def count_events_for_preset(cls, preset: str) -> Optional[int]:
        """Consulta eventos registrados en Wazuh para presets ('24h', '7d', '30d', '90d')."""
        if not cls._is_configured():
            return None
        mapping = {"24h": "now-24h", "7d": "now-7d", "30d": "now-30d", "90d": "now-90d"}
        preset_expr = mapping.get(preset)
        if not preset_expr:
            return None
        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_count"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {"query": {"range": {"@timestamp": {"gte": preset_expr}}}}
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=15.0) as client:
                resp = await client.post(url, auth=auth, json=query)
                if resp.status_code == 200:
                    return resp.json().get("count")
        except Exception as e:
            logger.warning("Fallo al contar preset %s en Wazuh: %s", preset, str(e))
        return None

    @classmethod
    async def get_decoders_stats(cls, start_date: date, end_date: date) -> Dict[str, Any]:
        """Agrega los decodificadores y retorna un dict con labels y values."""
        if not cls._is_configured():
            return {"labels": [], "values": [], "total": 0}
        start_iso = f"{start_date}T00:00:00.000Z"
        end_iso = f"{end_date}T23:59:59.999Z"
        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_search"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {
            "size": 0,
            "query": {"range": {"@timestamp": {"gte": start_iso, "lte": end_iso}}},
            "aggs": {"decoders": {"terms": {"field": "decoder.name", "size": 10}}},
        }
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=15.0) as client:
                resp = await client.post(url, auth=auth, json=query)
                if resp.status_code == 200:
                    aggs = resp.json().get("aggregations", {}).get("decoders", {}).get("buckets", [])
                    total = resp.json().get("hits", {}).get("total", {}).get("value", 0)
                    if isinstance(total, dict):
                        total = total.get("value", 0)
                    return {"labels": [b["key"] for b in aggs], "values": [b["doc_count"] for b in aggs], "total": total}
        except Exception as e:
            logger.warning("Fallo al obtener stats de decoders: %s", str(e))
        return {"labels": [], "values": [], "total": 0}
