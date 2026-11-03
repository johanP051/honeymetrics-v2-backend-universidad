# Escaneo de Seguridad Robusto — Ecosistema HoneyMetrics v2 (Universidad)

**Fecha:** 2026-10-08 · **Alcance:** `honeymetrics-v2-backend-universidad` (profundización) + `honeymetrics-v2-frontend-universidad` (primer escaneo) + `honeymetrics-frontend` (primer escaneo)
**Herramientas:** npm audit, bandit, pip-audit, greps OWASP dirigidos, revisión manual

---

## Resumen ejecutivo

| Proyecto | Critical | High | Medium | Nota |
|---|---|---|---|---|
| v2-backend-universidad | 0 | 1 (H1 webhook) | 3 | SAST limpio; hallazgos de auditoría previa persisten |
| v2-frontend-universidad | 2 (npm) | 8 (npm) + 2 propios | 4 | **14 vulns de dependencias**; JWT en localStorage |
| honeymetrics-frontend (v1) | 2 (npm) | 8 (npm) + 1 propio | 4 | Mismo árbol de deps; nginx sin cabeceras |

---

## 1. honeymetrics-v2-backend-universidad (profundización)

### Persisten (de auditoría del mismo día — ver informe SAST+DAST)
- **H1 ALTA**: webhook Telegram fail-open (confirmado en producción; plan de remediación ya acordado).
- **H2 MEDIA**: sin rate limiting (slowapi no implementado).
- **H3 MEDIA**: cabeceras de seguridad ausentes.
- **H4 MEDIA**: `.honey-back-venv/` (3.072 archivos) versionado.
- **H5/H6/H7 BAJA**: `int(user_id)` sin manejo; health expone `environment`; fallback sintético.

### Nuevos verificados
| ID | Severidad | Hallazgo | Evidencia |
|---|---|---|---|
| B1 | 🟡 BAJA | `DEBUG=True` por defecto en `config.py:11` y en `.env` local — **inerte**: `DEBUG` no se usa en ninguna línea de `app/` (solo `ENVIRONMENT`). Bajar a informativo; eliminar la variable muerta. | `grep settings.DEBUG` → 0 usos |
| B2 | ℹ️ INFO | `docker-compose.yml` (dev): `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres_password}` — aceptable en dev (`restart: "no"`); **verificar** que `docker-compose.prod.yml` no herede el default. | compose |
| B3 | ✅ | `scripts/seed_admin.py` **exige** `SEED_ADMIN_PASSWORD` (RuntimeError si falta) — no hay credenciales por defecto versionadas. | scripts/seed_admin.py:17-19 |
| B4 | ✅ | `WAZUH_TLS_VERIFY: bool = True` por defecto (corrige el patrón `verify=False` de v1). | config.py |
| B5 | ✅ | Validador de config: en `staging|production` exige `SECRET_KEY` (falla si falta). | config.py:63 |

---

## 2. honeymetrics-v2-frontend-universidad (PRIMER ESCANEO)

### Dependencias (npm audit — 14 vulnerabilidades)

| ID | Severidad | Paquete | Vector | Fix |
|---|---|---|---|---|
| F1 | 🔴 CRITICAL | `plotly.js@3.7.0` → `maplibre-gl` | **XSS: bypass del sanitizer DOM (`DOM.sanitize()` vía Live NamedNodeMap)** — se ejecuta en runtime en los dashboards | `plotly.js@4.1.2` (major, requiere pruebas de charts) |
| F2 | 🟠 HIGH | `axios@1.6.8` | Prototype pollution en fetch adapter → altera requests salientes | **`npm audit fix` no-breaking (axios ≥1.12)** |
| F3 | 🟠 HIGH | `vite@5.1.6` | Path traversal en dev-server (`.map` de deps optimizadas) + launch-editor NTLM (Windows) | `vite@8` (major) |
| F4 | 🟠 HIGH | `tailwindcss@3.4.19` → braces/micromatch/fast-glob | DoS por stack-exhaustion (build-time) | `tailwindcss@4` (major) |
| F5 | 🟠 HIGH | `source-map-js` | DoS event-loop (build-time) | `npm audit fix` (no-breaking) |
| F6 | 🟡 MODERATE | `esbuild`, `postcss-selector-parser` | Exposición del dev-server; CPU exhaustion | majors de vite/postcss |

**Quick win:** `npm audit fix` sin breaking changes elimina F2 y F5 (2 HIGH) en minutos.

### Código fuente
| ID | Severidad | Hallazgo |
|---|---|---|
| F7 | 🟠 MEDIA | **JWT en `localStorage`** (`access_token`, `user_data` en `AuthContext.jsx:32-37`): robable con XSS. Combinado con F1 (XSS de plotly en runtime) forma **cadena completa de robo de sesión**. Mitigación ideal: cookie httpOnly + CSRF; mitigación pragmática: priorizar F1/F2. |
| F8 | 🟡 BAJA | Ruta `/logs` fuera de `ProtectedRoute` en `main.jsx` (el backend sí protege la API, pero la vista queda montada sin guard). |
| F9 | 🟡 BAJA | Sin política global `no-store` (equivalente Django `never_cache`) — ya analizado: falta middleware en backend + manejo BFCache/`pageshow` en frontend. |
| ✅ | — | **0 superficie XSS en código propio** (ni `dangerouslySetInnerHTML`, ni `innerHTML`, ni `eval`); sin secretos versionados (solo `.env.example`); sin URLs de prod hardcodeadas (fallback `localhost:8001`); `vite.config.js` sin sourcemaps en build (default off); `wrangler`/deploy sin tokens. |

---

## 3. honeymetrics-frontend v1 (PRIMER ESCANEO)

### Dependencias: árbol idéntico al v2 → **aplican F1–F6** (mismos CRITICAL/HIGH).

### Código fuente / infraestructura
| ID | Severidad | Hallazgo |
|---|---|---|
| G1 | 🟠 MEDIA | `nginx.conf` **sin cabeceras de seguridad** (único `add_header` = `Cache-Control: immutable` para `/assets/`). Sin HSTS, XCTO, XFO, CSP, Referrer-Policy en un frontend productivo (Cloudflare Workers/Docker). |
| G2 | 🟡 BAJA | RBAC solo-cliente: `hm_role` en `localStorage` (`AuthContext.jsx:35`) es *gate* de UI suplantable. Autenticación real vía cookies (`withCredentials: true`) — **la enforcement debe estar en el backend v1** (auditoría previa: `threats/*` públicos). Documentar como UI-only. |
| G3 | ℹ️ INFO | `VITE_API_URL` con fallback `http://localhost:8000` (misma página https → mixed-content si se olvidó la variable en build). |
| ✅ | — | Sin secretos en `wrangler.jsonc` (solo assets + SPA fallback); `.env` no versionado; 0 superficie XSS propia; timeout de axios configurado (3s). |

---

## 4. Orden de remediación recomendado (consolidado)

1. **H1 backend**: fail-closed + `hmac.compare_digest` + rotación de secreto + pruebas + idempotencia (plan ya detallado por el usuario).
2. **`npm audit fix`** (no-breaking) en **ambos** frontends → elimina axios (F2) y source-map-js (F5).
3. **`plotly.js@4.1.2`** en ambos frontends (CRITICAL XSS runtime) + regresión de dashboards.
4. **Backend H2/H3**: rate limiting (slowapi ya en requirements) + middleware de cabeceras (incluye `Cache-Control: no-store` en rutas de auth — resuelve también F9/G1 parcial).
5. **Frontend v2**: envolver `/logs` en `ProtectedRoute` (F8) + BFCache/`pageshow`.
6. **nginx v1**: añadir cabeceras de seguridad (G1) o migrarlas al Worker de Cloudflare.
7. **Majors diferibles**: tailwind v4, vite v8 (vulns build-time, explotables solo en desarrollo).
8. **Fase IDOR autenticada** (requiere usuario `auditor` de prueba).
