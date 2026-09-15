# 🖥️ Regla de Hardware y Topología Distribuida (Wazuh y FastAPI)

Para el desarrollo del proyecto HoneyMetrics v2.0, el Agente debe respetar las siguientes restricciones de infraestructura:

1. **Nodos Separados (LAN):** 
   - **Nodo A (Intocable):** Wazuh (OpenSearch) se aloja en `192.168.32.11:9200`. NO se despliega código aquí.
   - **Nodo B (Backend Activo):** La API de FastAPI y PostgreSQL se alojan en el equipo con IP `192.168.31.112` (16GB de RAM).
2. **Protección de Memoria (Anti-OOM):** OpenSearch colapsa si se le piden muchos datos a la vez. En el Backend (FastAPI), todo endpoint que consulte a Wazuh debe usar **Paginación Defensiva (chunk_size <= 1000)** y **StreamingResponse** de Python (generadores) para evitar cargar el dataset completo en la memoria de la aplicación.
3. **Flujo de Red:** El Frontend (React) en Vercel jamás toca a Wazuh directamente. Todo pasa obligatoriamente por el proxy interno del Backend (FastAPI).
4. **Fuente de Verdad:** Si hay dudas arquitectónicas, consultar el diagrama en la bóveda de Obsidian: `20_Proyectos/HoneyMetrics/HoneyMetrics-Topologia-y-Redes.md`.
