# Informe de Auditoría de Seguridad — HoneyMetrics v2 API (UDEC)

**Fecha:** 2026-10-08 (UTC) · **Objetivo:** `https://api-honey-v2-homeserver.johan-d3v.site` (Cloudflare Tunnel → 192.168.31.235)
**Alcance:** SAST sobre `app/` + DAST/Caja negra + Path Traversal sobre la API desplegada (25 endpoints, `/api/v1/openapi.json`)
**Herramientas:** Bandit, pip-audit, revisión manual OWASP Top 10 2021, pruebas HTTP en vivo (curl/fetch)

---

## 1. Resumen ejecutivo

| # | Hallazgo | Severidad | CWE | Estado |
|---|----------|-----------|-----|--------|
| H1 | Webhook Telegram sin autenticación efectiva (fail-open) — **confirmado en producción** | 🔴 ALTA | CWE-306 / CWE-346 | Explotado en prueba |
| H2 | Sin rate limiting en login / forgot-password (slowapi declarado pero no implementado) | 🟠 MEDIA | CWE-307 | Confirmado (8×401, sin 429) |
| H3 | Cabeceras de seguridad ausentes (HSTS, XCTO, XFO, CSP, Referrer-Policy) | 🟠 MEDIA | CWE-693 | Confirmado |
| H4 | `.honey-back-venv/` versionado en git (3.072 archivos) | 🟠 MEDIA | CWE-1104 | Confirmado |
| H5 | `int(user_id)` sin manejo en `deps.py` → posible 500 con `sub` no numérico | 🟡 BAJA | CWE-209 | Requiere token |
| H6 | Health endpoint expone `environment: production` | 🟡 BAJA | CWE-200 | Informativo |
| H7 | Fallback de "dataset sintético" en `stream_jsonl_dataset` | 🟡 BAJA | Convención | Estático |

**Verificaciones superadas (✅):** control de acceso JWT en 13 endpoints sensibles (401 sin token), revocación `jti`, Argon2, ORM parametrizado (sin SQLi), CORS con orígenes explícitos, validación Pydantic estricta (422 sin stack traces), anti-enumeración en forgot-password, tokens malformados → 401 limpio (nunca 500), `alg=none` rechazado, métodos incorrectos → 405, `SECRET_KEY` de producción distinta a la del repo (forja de token → 401), Bandit 0 medium+, pip-audit 0 CVEs, `.env` NO versionado.

---

## 2. Hallazgos detallados

### H1 — 🔴 Webhook Telegram sin autenticación efectiva (ALTA)
**Ubicación:** `app/api/v1/endpoints/logs_endpoints.py:84`

```python
if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token:
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(403, ...)
```

La condición es **fail-open**: si el atacante **omite** el header `X-Telegram-Bot-Api-Secret-Token`, el bloque de validación se salta por completo.

**Evidencia en producción (2026-10-08):**
```
POST /api/v1/logs/webhook/telegram   (SIN header de secreto)
{"callback_query":{"id":"audit-test-callback-1","data":"approve_audit-test-export-000",
 "message":{"message_id":1,"chat":{"id":1}}}}
→ 200 {"status":"success","export_id":"audit-test-export-000","action":"APROBADA"}  (2.8s = llamadas reales a api.telegram.org)
```

**Impacto:**
1. Aprobación/rechazo **no autenticado** de exportaciones de logs (`LogsService.update_export_status`) — rompe la integridad del flujo de aprobación (A01 Broken Access Control).
2. El servidor actúa como relé de la API de Telegram (`answerCallbackQuery`, `editMessageText`) con `chat_id`/`message_id` controlados por el atacante → spam o mensajes engañosos en chats donde el bot esté presente.

**Fix recomendado (fail-closed + comparación constante):**
```python
import hmac
if not settings.TELEGRAM_WEBHOOK_SECRET or \
   not x_telegram_bot_api_secret_token or \
   not hmac.compare_digest(x_telegram_bot_api_secret_token, settings.TELEGRAM_WEBHOOK_SECRET):
    raise HTTPException(status_code=403, detail="Token secreto de webhook inválido o ausente.")
```

### H2 — 🟠 Sin rate limiting en autenticación (MEDIA)
`slowapi>=0.1.9` figura en `requirements.txt` pero **no existe ningún uso de `Limiter`** en `app/` (0 coincidencias). Evidencia dinámica: 8 POST consecutivos a `/api/v1/auth/login` → `401 401 401 401 401 401 401 401` (ningún `429`).
**Impacto:** fuerza bruta de credenciales y *email bombing* vía `/auth/forgot-password` (dispara correos reales de Resend sin límite).
**Fix:** aplicar `Limiter` con p.ej. `5/minute` por IP en `login`, `verify-login` y `forgot-password`.

### H3 — 🟠 Cabeceras de seguridad ausentes (MEDIA)
Respuesta de `GET /` solo incluye `server: cloudflare`. Faltan:
`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy`.
**Fix:** middleware ligero que las añada a toda respuesta (A05 Security Misconfiguration).

### H4 — 🟠 Venv versionado en git (MEDIA)
`git ls-files | grep -c "^\.honey-back-venv/"` → **3072 archivos**. Añadir `.honey-back-venv/` a `.gitignore` y removerlo del índice (`git rm -r --cached`).

### H5 — 🟡 `int(user_id)` sin try/except en `app/api/deps.py`
Un JWT válido con `sub` no numérico genera `ValueError` → 500. Rodear con try/except y responder 401.

### H6 — 🟡 `/api/v1/threats/health` expone `environment: production`
Informativo; no expone secretos, pero reduce entropía de reconocimiento.

### H7 — 🟡 Fallback de datos sintéticos en `logs_service.stream_jsonl_dataset`
Si no hay archivos fuente, emite `"Dataset sintetico de desarrollo"` — colisión con la regla de cero datos sintéticos en producción. Preferir 404/204 explícito.

---

## 3. Path Traversal (CWE-22) — Resultado: NO explotable ✅

**Estrategia de defensa verificada (estática + dinámica):** el `export_id` del path **nunca** construye rutas de archivo. Los `open()` usan `LOCAL_STORAGE_DIR` fijo + nombres derivados de objetos `date` (no strings del cliente) o de rutas candidatas constantes. El id solo se usa para lookup en DB.

**Payloads probados sobre `/api/v1/logs/download/{id}` y `/logs/report-stats/{id}` con `--path-as-is`:**

| Payload | Resultado |
|---|---|
| `..%2f..%2f..%2fetc%2fpasswd` | 404 (fuera de ruta) |
| `%2e%2e%2f%2e%2e%2fetc%2fpasswd` | 404 |
| `....%2f%2f....%2f%2fetc%2fpasswd` | 404 |
| `..%252f..%252fetc%252fpasswd` (doble encode) | 401 (llega a ruta, requiere JWT) |
| `..%5c..%5c..%5cetc%5cpasswd` (backslash) | 401 |
| `%2fetc%2fpasswd` (absoluto) | 404 |
| `test%00.jsonl` (null byte) | 400 — bloqueado por Cloudflare en el edge |

Sin token autenticado no se alcanza el handler; el análisis estático confirma que tampoco habría escape de directorio. **Inyección CRLF** en `Content-Disposition` (filename derivado de `export_id`) quedó como riesgo residual bajo: uvicorn/h11 valida los valores de header.

---

## 4. Matriz de pruebas dinámicas (caja negra)

| Prueba | Resultado |
|---|---|
| 13 endpoints sensibles sin token | ✅ 401 + `WWW-Authenticate: Bearer` |
| `threats/health` sin token | 200 público (esperado) |
| CORS con origen `https://evil-attacker.com` | ✅ 400 "Disallowed CORS origin" |
| Preflight OPTIONS login (origen evil) | ✅ rechazado |
| TRACE / OPTIONS / GET en login | ✅ 405 |
| Tokens malformados (`null`, `abc.def.ghi`, vacío) | ✅ 401 limpio, sin 500 |
| JWT `alg=none` forjado | ✅ 401 (algoritmo fijado en decode) |
| Token forjado con `SECRET_KEY` del repo | ✅ 401 (secret de prod distinto) |
| JSON malformado / tipos confusos | ✅ 422 Pydantic, sin stack traces |
| SQLi en login (`' OR '1'='1`) | ✅ 422 por validador de email; ORM parametrizado |
| SQLi en query `range` de threats/summary | Requiere token (ORM parametrizado por diseño) |
| Anti-enumeración forgot-password (2 correos falsos) | ✅ respuestas idénticas 200 |
| Rate limit login (8 intentos) | ❌ sin 429 → H2 |
| Webhook sin secreto (flujo completo) | ❌ 200 `APROBADA` → H1 |

---

## 5. Pendientes (requieren credenciales de prueba)
- **IDOR** en `/blacklist/{entry_id}` y `/admin/users/{user_id}` (modificación cruzada entre usuarios/roles) — se necesita un token de usuario estándar y uno admin.
- Descarga de exportaciones ajenas entre usuarios (`/logs/download/{id}` con token de otro usuario).
- Prueba de `must_change_password` y expiración real de tokens.

**Sugerencia:** crear un usuario `auditor` de prueba (rol estándar) para completar la fase autenticada.
