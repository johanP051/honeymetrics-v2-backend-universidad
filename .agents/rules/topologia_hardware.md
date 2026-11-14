# 🖥️ Regla de Hardware y Topología Distribuida (Wazuh y FastAPI)

Para el desarrollo del proyecto HoneyMetrics v2.0, el Agente debe respetar las siguientes restricciones de infraestructura:

1. **Nodos Separados (LAN):** 
   - **Nodo A / Wazuh (Intocable):** Wazuh (OpenSearch) se aloja en `192.168.32.11:9200`. NO se despliega código aquí.
   - **Nodo 2 (Backend Activo — HoneyMetrics v1 y v2):** La API de FastAPI (`hm_v2_api`), PostgreSQL (`hm_v2_db`, `127.0.0.1:5434->5432`) y `hm_v2_api_cloudflared` se alojan en **`sebas@192.168.33.2`** (`~/honeymetrics-v2-backend-universidad`, rama `main`).
   - **Nodo 1 (`jsebas@192.168.31.235`):** NO es el host activo de HoneyMetrics v2 (aloja Taiga y otros servicios).
2. **Protección de Memoria (Anti-OOM):** OpenSearch colapsa si se le piden muchos datos a la vez. En el Backend (FastAPI), todo endpoint que consulte a Wazuh debe usar **Paginación Defensiva (chunk_size <= 1000)** y **StreamingResponse** de Python (generadores) para evitar cargar el dataset completo en la memoria de la aplicación.
3. **Flujo de Red:** El Frontend (React SPA) en **Cloudflare Workers** (`https://honeymetrics-v2-frontend.johan-sebastianposada.workers.dev`) jamás toca a Wazuh directamente. Todo pasa por `https://api-honey-v2-homeserver.johan-d3v.site` hacia el proxy interno del Backend (FastAPI) en el Nodo 2.
4. **Fuente de Verdad:** Consultar `~/INFRA.md` en cada servidor, Engram (`engram search "HoneyMetrics"`), o la bóveda de Obsidian (`20_Proyectos/HoneyMetrics/HoneyMetrics-Topologia-y-Redes.md`).
