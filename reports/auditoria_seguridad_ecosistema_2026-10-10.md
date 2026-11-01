# Auditoría Robusta de Ciberseguridad — Ecosistema HoneyMetrics (2026-10-10)

**Ejecución del prompt de auditoría AppSec** · Alcance: `honeymetrics-backend` (v1), `honeymetrics-frontend` (v1), `honeymetrics-v2-backend-universidad`, `honeymetrics-v2-frontend-universidad`, `honeymetrics-documentacion`, `honeymetrics-v2-documentacion-universidad`, `honeymetrics-sustentacion-20-mayo`
**DAST en vivo:** `https://api-honey-v2-homeserver.johan-d3v.site` (Cloudflare Tunnel → 192.168.31.235) + `https://honeymetrics-frontend.johan-sebastianposada.workers.dev`
**Credenciales de prueba:** NO HAY → **Fase 4 autenticada PENDIENTE** (proponer usuario `auditor`)
**Herramientas:** bandit, pip-audit, npm audit, greps OWASP/CWE dirigidos, revisión manual archivo por archivo, probes HTTP benignos

---

## 1. Resumen ejecutivo

| # | Proyecto | Hallazgo | Sev. | CWE | Estado vs auditoría 2026-10-07/08 |
|---|----------|----------|------|-----|-----------------------------------|
| E1 | docs | **Token de Telegram VÁLIDO Y ACTIVO versionado** en `guia-despliegue.md:381` (bot `@honeyemtrics_backend_bot`, verificado vía `getMe ok:true`) | 🔴 HIGH | CWE-798 | **NUEVO** |
| E2 | v2-backend | Webhook Telegram fail-open (validación se salta si no llega header) — **re-explotado en vivo 10-oct** | 🔴 HIGH | CWE-306 | **PERSISTE** |
| E3 | v1-backend | `.dockerignore` sin `.env` + `COPY . .` → secretos (Resend/Telegram/Wazuh/IRIS) en capas de imagen | 🔴 HIGH | CWE-798 | **PERSISTE** |
| E4 | v2-backend | Ídem: sin `.dockerignore` + `Dockerfile:28 COPY --chown=appuser . .` → `.env` productivo horneado en imagen | 🟠 MEDIUM | CWE-200 | **NUEVO (v2)** |
| E5 | v1-backend | Bypass parcial de MFA: token `mfa_pending` aceptado como sesión plena por `get_current_user` (ventana de 5 min post-robo de contraseña) | 🟠 MEDIUM | CWE-308 | **NUEVO** |
| E6 | ambos frontends | 14 vulns npm (2 CRITICAL: `plotly.js`→maplibre XSS runtime; 8 HIGH: axios prototype pollution con fix no-breaking, tailwind/vite/source-map-js) | 🟠 MEDIUM* | CWE-1104 | **PERSISTE** (sin cambios) |
| E7 | v2-backend | Sin rate limiting (slowapi no implementado) — re-probado: 8×401, ningún 429 | 🟠 MEDIUM | CWE-307 | **PERSISTE** |
| E8 | v2-backend | Cabeceras de seguridad ausentes (HSTS/XCTO/XFO/CSP/RP/PP = null) — re-probado | 🟠 MEDIUM | CWE-693 | **PERSISTE** |
| E9 | v1-backend | Cookies `samesite="none"` sin token CSRF + `allow_credentials=True` | 🟠 MEDIUM | CWE-352 | PERSISTE |
| E10 | v1-backend | Rate-limit con `get_remote_address` detrás de proxy (bucket global) y cobertura solo en auth | 🟠 MEDIUM | CWE-770 | PERSISTE |
| E11 | v1-backend | `totp_secret` y `reset_token` en plano en BD | 🟠 MEDIUM | CWE-312 | PERSISTE |
| E12 | v1-backend | PRNG no criptográfico para contraseñas temporales (`random.choice`) | 🟠 MEDIUM | CWE-338 | PARCIAL (export_id ya usa `secrets`) |
| E13 | v1-backend | Security headers/TrustedHost ausentes; docs/redoc públicos incondicionales | 🟠 MEDIUM | CWE-693 | PERSISTE |
| E14 | v1-backend | Carrera en logout concurrente → `IntegrityError` no manejado = 500 (índice único existe) | 🟡 LOW | CWE-362 | NUEVO |
| E15 | v1-backend | Denylist `RevokedToken` sin purga de expirados (crecimiento indefinido en hot path) | 🟡 LOW | CWE-400 | NUEVO |
| E16 | v1-backend | `export_id` inyectado sin escapar en línea JSONL de error (f-string) | 🟡 LOW | CWE-20 | NUEVO |
| E17 | v1-backend | `Content-Disposition` con input sin sanitizar (regex `^EXP-[A-F0-9]{8}$` sugerida) | 🟡 LOW | CWE-113 | NUEVO |
| E18 | v1-backend | `joblib.load` (pickle→RCE potencial) sin comparación de hash antes de cargar | 🟡 LOW | CWE-502 | NUEVO |
| E19 | v1-backend | compose dev: fallback `postgres_password` + puerto 5432 publicado (override) | 🟡 LOW | CWE-1188 | PARCIAL (prod endurecido) |
| E20 | v1-backend | Descarga de exports sin binding de propietario (cualquier Analista descarga cualquier export) | 🟡 LOW | CWE-639 | NUEVO |
| E21 | v1-backend | 2× `verify=False` (CWE-295) en scripts IRIS + 1 request sin timeout | 🟡 LOW | CWE-295/400 | PERSISTE (bandit) |
| E22 | docs | 28 referencias a IPs de infraestructura interna (SIEM 192.168.32.11, QA .235) en repos posiblemente públicos | ⚪ INFO | CWE-200 | NUEVO |
| E23 | v1-frontend | SPA fallback responde 200 a todo (incl. `/.env`) — verificado: sirve index.html, NO fuga | ⚪ INFO | — | Descartado |

*E6 sube a HIGH de negocio por la cadena XSS-runtime + JWT-en-localStorage en v2-frontend.

### ✅ CORREGIDOS desde la auditoría 2026-10-07 (v1 backend — pendientes de commit, están en working tree)
1. **`/threats/*` ahora exige roles** (`RoleChecker` en router, threats.py:13-26) — cierra la fuga de telemetría CTI.
2. **Ingesta Wazuh fail-closed**: 503 sin config + `hmac.compare_digest` (ingest.py:9-19) — elimina el token hardcodeado.
3. **Webhook Telegram v1 fail-closed**: 503 sin secreto + `hmac.compare_digest` (logs.py:76-83).
4. **JWT con `jti` + revocación en logout**: guard verificado en TODOS los routers vía `get_current_user` (deps.py:37-44); tokens legacy documentados.
5. **Validador de `SECRET_KEY` obligatorio en staging/prod** + clave efímera en dev (config.py:110-129).

---

## 2. Hallazgos con evidencia (los accionables esta semana)

### E1 — 🔴 Token de Telegram activo versionado en documentación
- **Ubicación:** `honeymetrics-documentacion/docs/guia-despliegue.md:381` — `export TELEGRAM_BOT_TOKEN="8844021545:AA…"` (enmascarado)
- **Evidencia empírica:** `curl https://api.telegram.org/bot<TOKEN>/getMe` → `{"ok":true,"result":{"id":8844021545,"is_bot":true,"username":"honeyemtrics_backend_bot"}}`
- **Impacto:** control total del bot (lectura de mensajes en grupos donde sea admin, envío de alertas, recepción de updates del flujo de aprobaciones). El bot ID difiere del actual en producción (8675166929…) → probablemente bot v1 aún vivo.
- **Mitigación:** revocar vía @BotFather (`/revoke`), actualizar el bot usado, reemplazar el valor en docs por `{{TELEGRAM_BOT_TOKEN}}`, rotar si ese bot sigue en algún despliegue.

### E2 — 🔴 Webhook Telegram v2 fail-open (re-confirmado en producción 2026-10-10)
- **Ubicación:** `honeymetrics-v2-backend-universidad/app/api/v1/endpoints/logs_endpoints.py:84` — `if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token:`
- **Evidencia empírica (10-oct):** `POST /api/v1/logs/webhook/telegram` SIN header → `200 {"status":"success","export_id":"delta-test-000","action":"APROBADA"}`
- **Mitigación:** fail-closed (503 sin config / 403 sin header o inválido) + `hmac.compare_digest` + validar `chat_id == ADMIN_TELEGRAM_CHAT_ID` + idempotencia (plan ya acordado por el usuario).

### E3/E4 — Secretos del `.env` dentro de las imágenes Docker
- **v1:** `.dockerignore` sin `.env` + `Dockerfile:28 COPY --chown=appuser:appuser . .` (claves: RESEND_API_KEY, TELEGRAM_BOT_TOKEN, POSTGRES_PASSWORD, WAZUH_INDEXER_PASSWORD, IRIS_API_KEY).
- **v2:** no existe `.dockerignore`; `Dockerfile:28` `COPY --chown=appuser:appuser . .` → mismo vector.
- **Mitigación:** crear/actualizar `.dockerignore` (`.env`, `.env.*`, `docker-compose*.yml`, `AI-passwds/`, `reports/`) y cargar secretos solo en runtime (`env_file`); reconstruir imágenes tras rotar.

### E5 — 🟠 Bypass parcial de MFA (v1, NUEVO)
- **Ubicación:** `auth_service.py:22-23` (emite `mfa_pending=True`) + `deps.py:31` (guard solo exige `sub`).
- **Impacto:** contraseña robada de un analista con 2FA → JWT de 5 min aceptado como sesión completa sin TOTP.
- **Mitigación:** en `get_current_user`, rechazar `payload.get("mfa_pending")` salvo en la ruta `mfa/verify-login`.

---

## 3. Defensas verificadas (aspectos positivos)

- **v1 backend**: bcrypt, anti-enumeración forgot-password, rate-limit en las 5 rutas de auth, MFA TOTP, RBAC en los 10 routers de negocio (verificado uno a uno — cero endpoints de negocio sin guard), 100% ORM parametrizado (0 SQL crudo), sin SSRF (0 URLs de usuario), sin path traversal (0 `open()` con input), sin mass assignment (schemas Pydantic explícitos), Docker non-root uid 1001 + multi-stage + `expose`, `hmac.compare_digest` en todos los secretos nuevos, validador de settings productivo, hashing de integridad ML + escritura atómica.
- **v2 backend**: control de acceso sostenido en vivo (401 en admin/logs/threats sin token), MFA TOTP con suite TDD, CI con gates QA, anti-enumeración, CORS explícito, `.env` jamás versionado (verificado en historial de los 4 repos), seed sin contraseñas default.
- **Frontends**: bundles sin secretos ni sourcemaps, 0 superficie XSS propia, wrangler sin tokens, interceptor 401→logout.

## 4. Matriz de pruebas ejecutadas

| Prueba | v1-backend | v2-backend | v1-front | v2-front | docs |
|---|---|---|---|---|---|
| SAST linter | ✅ bandit (2H/1M/29L) | ✅ (10-07: 0 M+) | n/a | n/a | n/a |
| Dependencias | ✅ pip-audit 0 CVE | ✅ 0 CVE | ✅ 14 vulns | ✅ 14 vulns | n/a |
| Secretos repo/historial | ✅ limpio | ✅ limpio | ✅ limpio | ✅ limpio | ❌ token vivo |
| Docker/config | ❌ E3 | ⚠️ E4 | ✅ wrangler limpio | ✅ | n/a |
| Access control sin auth | ✅ código (RBAC 10 routers) | ✅ en vivo 401 | n/a | n/a | n/a |
| DAST cabeceras | ⏸️ sin URL prod | ❌ E8 | ❌ sin headers | n/a | n/a |
| Rate limiting | ⚠️ E10 | ❌ E7 | n/a | n/a | n/a |
| Webhook bypass | ✅ corregido (código) | ❌ E2 en vivo | n/a | n/a | n/a |
| Path traversal | ✅ descartado (rutas fijas) | ✅ descartado (10-07) | ✅ bundles | ✅ | n/a |
| Mass assignment / SSRF / SQLi | ✅ verificado seguro | ✅ ORM | n/a | n/a | n/a |
| **IDOR / RBAC autenticado** | ⏸️ **sin credenciales** | ⏸️ **sin credenciales** | ⏸️ | ⏸️ | n/a |
| Robustez entrada (JSON/tokens/alg=none) | ⏸️ sin URL | ✅ 10-07 | n/a | n/a | n/a |

## 5. Plan de remediación priorizado

**Quick-wins (≤1 día):**
1. **E1**: revocar/rotar token de Telegram del docs + placeholder en la guía (10 min, reduce exposición real).
2. **Committear los fixes v1 ya hechos** (threats/ingest/webhook/SECRET_KEY) — están solo en working tree; un `git clean` los perdería.
3. **E3/E4**: `.dockerignore` en ambos backends + rebuild.
4. **E6 quick-win**: `npm audit fix` no-breaking en ambos frontends (axios + source-map-js).

**Esta sprint:**
5. **E2**: fail-closed webhook v2 + rotación de secreto + pruebas + idempotencia (plan acordado 10-07).
6. **E5**: rechazar `mfa_pending` en `get_current_user` (TDD: test rojo → fix → triangulación).
7. **E7/E8**: slowapi con keying por `X-Forwarded-For` confiable + middleware de cabeceras (v2) y (v1) E9/E13.
8. **E10**: keying del limiter detrás de Cloudflare; **E12**: `secrets.choice` en contraseñas temporales; **E15**: purga programada de `RevokedToken`.

**Diferibles:** E11 (cifrado Fernet), E14/E16/E17/E18/E19/E20 (hardening LOW), E22 (revisar visibilidad de repos de docs).

**Pendiente de evaluación (requiere credenciales):** Fase 4 completa — IDOR/BOLA, escalamiento vertical, revocación real de sesión, flujos reset/OTP en v1 y v2. **Propuesta: crear usuario `auditor` (rol Analista) en cada entorno.**

## 6. No Evaluado (declarado, no inventado)
- DAST v1-backend: sin URL productiva pública (solo placeholder `api.tu-dominio.com`).
- CRLF explotable en runtime (v1 logs.py) y efectividad real del rate-limit tras Cloudflare: requieren ejecutar la app.
- Capas de imagen ya construidas en el homeserver (`docker history`): requiere acceso al daemon remoto.
- Integridad de `.joblib` en disco vs. hashes publicados: hashes viven en el despliegue remoto.
