import ipaddress
import logging
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings
from app.services.wazuh_scroll import WazuhScrollService
from app.services.wazuh_stats import WazuhStatsService

logger = logging.getLogger(__name__)


def extract_country_from_hit(source_dict: dict) -> str:
    """Extrae el país de procedencia en cascada desde un documento de evento Wazuh."""
    data = source_dict.get("data", {}) if isinstance(source_dict, dict) else {}
    geo = source_dict.get("GeoLocation", {}) if isinstance(source_dict, dict) else {}
    abuse = data.get("abuseipdb", {}) if isinstance(data, dict) else {}
    return (
        (geo.get("country_name") if isinstance(geo, dict) else None)
        or (abuse.get("country") if isinstance(abuse, dict) else None)
        or (abuse.get("country_code") if isinstance(abuse, dict) else None)
        or (data.get("country") if isinstance(data, dict) else None)
        or "Unknown"
    )


class WazuhExtractor:
    """
    Servicio de Ingesta Asíncrona desde Wazuh Indexer (OpenSearch).
    Extrae telemetría de eventos crudos y consolida métricas CTI.
    """

    extract_day_to_jsonl = WazuhScrollService.extract_day_to_jsonl
    extract_logs_scroll = WazuhScrollService.extract_logs_scroll
    count_events_for_range = WazuhStatsService.count_events_for_range
    count_events_for_preset = WazuhStatsService.count_events_for_preset
    get_decoders_stats = WazuhStatsService.get_decoders_stats

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica si las credenciales mínimas de Wazuh están configuradas."""
        return bool(settings.WAZUH_INDEXER_URL and settings.WAZUH_INDEXER_USER and settings.WAZUH_INDEXER_PASSWORD)

    @classmethod
    async def check_connection(cls) -> bool:
        """Realiza un health check profundo a Wazuh."""
        if not cls.is_configured():
            return False
        url = f"{settings.WAZUH_INDEXER_URL}/_cluster/health"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=5.0) as client:
                response = await client.get(url, auth=auth)
                return response.status_code == 200
        except Exception as e:
            logger.warning("Wazuh health check failed: %s", str(e))
            return False

    @classmethod
    async def get_recent_attackers(cls) -> Optional[List[Dict[str, Any]]]:
        """Obtiene las IPs atacantes y sus métricas desde Wazuh mediante aggregations."""
        if not await cls.check_connection():
            return None
        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_search"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {
            "size": 0,
            "aggs": {
                "top_ips": {
                    "terms": {"field": "data.srcip", "size": 50},
                    "aggs": {
                        "severity": {"avg": {"field": "rule.level"}},
                        "users": {"terms": {"field": "data.dstuser"}},
                        "tactics": {"terms": {"field": "rule.mitre.tactic"}},
                        "months": {"date_histogram": {"field": "@timestamp", "calendar_interval": "month"}},
                        "sample_hit": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": [
                                        "GeoLocation.country_name",
                                        "data.abuseipdb.country",
                                        "data.abuseipdb.country_code",
                                        "data.country",
                                    ]
                                },
                            }
                        },
                    },
                }
            },
        }
        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=10.0) as client:
                resp = await client.post(url, auth=auth, json=query)
                if resp.status_code == 200:
                    aggs = resp.json().get("aggregations", {}).get("top_ips", {}).get("buckets", [])
                    results = []
                    for bucket in aggs:
                        raw_ip = str(bucket.get("key", "")).strip()
                        clean_ip = raw_ip
                        if ":" in clean_ip:
                            prefix, sep, suffix = clean_ip.partition(":")
                            if any(p in prefix.lower() for p in ("tcp", "udp", "ip")) or (clean_ip.count(":") == 1 and not suffix.isdigit()):
                                clean_ip = suffix.strip()

                        try:
                            ip_obj = ipaddress.ip_address(clean_ip)
                            if ip_obj.is_unspecified or ip_obj.is_loopback:
                                continue
                            clean_ip = str(ip_obj)
                        except ValueError:
                            continue

                        top_hits = bucket.get("sample_hit", {}).get("hits", {}).get("hits", [])
                        hit_source = top_hits[0].get("_source", {}) if top_hits else {}
                        country = extract_country_from_hit(hit_source)

                        results.append(
                            {
                                "ip": clean_ip,
                                "country": country,
                                "total_events": bucket["doc_count"],
                                "months": [b["key_as_string"] for b in bucket.get("months", {}).get("buckets", [])],
                                "avg_severity": bucket.get("severity", {}).get("value", 5.0) or 5.0,
                                "badge": "Dynamic Threat",
                                "primary_tactic": (
                                    bucket.get("tactics", {}).get("buckets", [{"key": "Unknown"}])[0]["key"]
                                    if bucket.get("tactics", {}).get("buckets")
                                    else "Unknown"
                                ),
                                "users": [b["key"] for b in bucket.get("users", {}).get("buckets", [])],
                            }
                        )
                    return results
        except Exception as e:
            logger.warning("Fallo al obtener atacantes recientes de Wazuh: %s", str(e))
        return None
