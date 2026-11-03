---
name: global-devops-deployment
description: >-
  Estándar de Infraestructura Híbrida, Docker Non-Root, Loopback Binding, Redes Homelab,
  Cloudflare Zero Trust Tunnels, Deploy Keys SSH y Kubernetes (k8s).
---

# 🚀 Hybrid Infrastructure, DevOps & Cloud-Native Deployment Standard

## 1. Topología Homelab y Matriz Global de Puertos (`INFRASTRUCTURE.md`)
Todo repositorio debe mantener en su raíz el archivo canónico `INFRASTRUCTURE.md` con la tabla global de puertos:
- **`192.168.33.2` (Homeserver Nodo 1):** `:22` (SSH), `:80` (`vuelos_fe`), `:5432` (`vuelos_db`), `127.0.0.1:5433:5432` (`hm_db` Loopback), `:6379` (Redis), `:8080` (Citas API).
- **`192.168.31.235` (Homeserver Nodo 2 / UDEC):** `:9000` (Taiga Platform), stack `v2-universidad`.
- **`192.168.32.11` (Nodo SIEM):** `:9200` (Wazuh Indexer OpenSearch), `:8443` (MISP), `:8090` (OpenCTI).
- **Regla:** Consultar `INFRASTRUCTURE.md` antes de asignar cualquier puerto para evitar colisiones.

## 2. Docker, Seguridad Loopback y Persistencia sin PyPI
1. **Loopback-Only Binding para Bases de Datos:**
   - Prohibido publicar bases de datos en `0.0.0.0`. Publicar siempre atado exclusivamente a loopback:
     ```yaml
     ports:
       - "127.0.0.1:5433:5432"
     ```
   - Permite acceso 100% determinista vía Túnel SSH en DBeaver sin exponer el puerto a la red local.
2. **Persistencia y Despliegues Offline (Homeserver sin PyPI):**
   - En `docker-compose.prod.yml`, montar volúmenes de código en solo lectura:
     ```yaml
     volumes:
       - ./app:/app/app:ro
       - ./alembic:/app/alembic:ro
     ```
   - Permite aplicar cambios de código mediante `git pull` + `docker compose up -d --no-deps api` sin necesidad de conectarse a PyPI.
3. **Recarga de Variables de Entorno en Docker:**
   - `docker compose restart api` **NO** recarga cambios de `.env`. El comando canónico obligatorio es:
     ```bash
     docker compose up -d --no-deps api
     ```
4. **Deploy Keys SSH de Solo Lectura:**
   - En servidores de producción, clonar exclusivamente mediante llaves `ed25519` con permiso *Read-Only* en GitHub usando alias en `~/.ssh/config` (`Host github.com-hm-deploy`).

## 3. Cloudflare Zero Trust Tunnels y Workers
1. **Nomenclatura Estricta:** Nombrar túneles como `<proyecto>-<servicio>-<entorno>-<nodo>` (ej. `api-honey-master-homeserver`).
2. **Tokens Seguros:** Prohibido `--token` en comandos CLI. Usar `TUNNEL_TOKEN_FILE=/etc/cloudflared/token` con montaje `:ro`.
3. **SPAs en Cloudflare:** En `wrangler.jsonc`, configurar `"not_found_handling": "single-page-application"`.
