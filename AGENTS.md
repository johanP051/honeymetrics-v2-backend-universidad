# HoneyMetrics Académico Backend

Consulta `.agents/rules/` antes de cambios Git, CI o despliegues. Este repositorio usa el perfil académico: rama auxiliar → `develop` → `QA` → `main`. Conserva las reglas de arquitectura, Scrum, seguridad y ML existentes.

- **Despliegue vivo del backend:** Nodo 2 (`ssh sebas@192.168.33.2`, `~/honeymetrics-v2-backend-universidad`, contenedores `hm_v2_api` + `hm_v2_db` + `hm_v2_api_cloudflared`). No desplegar en `192.168.31.235`.
- **Memoria persistente:** Ante dudas de infraestructura o topología entre proyectos, consultar `~/INFRA.md` o Engram (`engram search`).
