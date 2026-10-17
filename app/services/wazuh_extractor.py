import ipaddress
import json
import logging
import os
from datetime import date
from typing import Dict, Any, List, Optional
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
                        "months": {
                            "date_histogram": {
                                "field": "@timestamp",
                                "calendar_interval": "month",
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
                            if clean_ip == "0.0.0.0" or ip_obj.is_unspecified:
                                continue
                            clean_ip = str(ip_obj)
                        except ValueError:
                            continue

                        results.append(
                            {
                                "ip": clean_ip,
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

    @classmethod
    async def count_events_for_range(cls, start_date: date, end_date: date) -> int:
        """
        Consulta la cantidad de eventos registrados en Wazuh para un rango de fechas.
        """
        if not cls.is_configured():
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
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=15.0) as client:
                response = await client.post(url, auth=auth, json=query)
                if response.status_code == 200:
                    return int(response.json().get("count", 0))
        except Exception as e:
            logger.warning("No se pudo conectar a Wazuh Indexer para contar eventos: %s", str(e))
        return 0

    @classmethod
    async def count_events_for_preset(cls, preset: str) -> Optional[int]:
        """
        Consulta la cantidad de eventos registrados en Wazuh para un preset temporal ('24h', '7d', '30d', '90d').
        """
        if not cls.is_configured():
            return None

        preset_mapping = {
            "24h": "now-24h",
            "7d": "now-7d",
            "30d": "now-30d",
            "90d": "now-90d",
        }
        preset_expr = preset_mapping.get(preset)
        if not preset_expr:
            return None

        url = f"{settings.WAZUH_INDEXER_URL}/wazuh-alerts-*/_count"
        auth = (settings.WAZUH_INDEXER_USER, settings.WAZUH_INDEXER_PASSWORD)
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": preset_expr
                    }
                }
            }
        }

        try:
            async with httpx.AsyncClient(verify=settings.WAZUH_TLS_VERIFY, timeout=15.0) as client:
                response = await client.post(url, auth=auth, json=query)
                if response.status_code == 200:
                    return response.json().get("count")
        except Exception as e:
            logger.warning("No se pudo conectar a Wazuh Indexer para contar preset %s: %s", preset, str(e))
        return None

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
                    logger.warning(
                        "Wazuh respondió con error HTTP %d al iniciar scroll.",
                        resp.status_code,
                    )
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
                            json={"scroll": "2m", "scroll_id": scroll_id},
                        )
                        if scroll_resp.status_code != 200:
                            break
                        scroll_data = scroll_resp.json()
                        scroll_id = scroll_data.get("_scroll_id")
                        hits = scroll_data.get("hits", {}).get("hits", [])

            logger.info(
                "Extracción completada para %s: %d eventos guardados en %s",
                target_date,
                extracted_count,
                file_path,
            )
            return file_path

        except Exception as e:
            logger.error(
                "Error durante la extracción de logs de Wazuh para %s: %s",
                target_date,
                str(e),
            )
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
    async def extract_logs_scroll(cls, start_date: date, end_date: date, chunk_size: int = 5000):
        """Extrae logs usando Scroll API para un rango de fechas."""
        if not cls.is_configured():
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
                    logger.warning(
                        "Wazuh respondió con error HTTP %d al iniciar scroll.",
                        resp.status_code,
                    )
                    return

                data = resp.json()
                scroll_id = data.get("_scroll_id")
                hits = data.get("hits", {}).get("hits", [])

                while hits:
                    for hit in hits:
                        yield hit.get("_source", {})

                    scroll_url = f"{settings.WAZUH_INDEXER_URL}/_search/scroll"
                    scroll_resp = await client.post(
                        scroll_url,
                        auth=auth,
                        json={"scroll": "2m", "scroll_id": scroll_id},
                    )
                    if scroll_resp.status_code != 200:
                        break
                    scroll_data = scroll_resp.json()
                    scroll_id = scroll_data.get("_scroll_id")
                    hits = scroll_data.get("hits", {}).get("hits", [])
        except Exception as e:
            logger.error("Error durante extract_logs_scroll: %s", str(e))
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
    async def get_decoders_stats(cls, start_date: date, end_date: date) -> Dict[str, Any]:
        """Agrega los decodificadores y retorna un dict con labels y values."""
        if not cls.is_configured():
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
                    labels = [b["key"] for b in aggs]
                    values = [b["doc_count"] for b in aggs]
                    return {"labels": labels, "values": values, "total": total}
        except Exception as e:
            logger.warning("Fallo al obtener stats de decoders: %s", str(e))

        return {"labels": [], "values": [], "total": 0}
