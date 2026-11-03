---
name: global-security-sast
description: >-
  Estándar enciclopédico de Seguridad de Aplicaciones (Omni-AppSec), SAST, OWASP Top 10 Web,
  OWASP API Security Top 10, OWASP ASVS 4.0.3 (V2.1/V2.8), CWE Top 25 y OWASP LLM Top 10.
---

# 🛡️ Global AppSec, SAST & Automated Pentesting Standard (Omni-AppSec)

## 🛠️ FASE A: LOS 12 DOMINIOS DE CODIFICACIÓN SEGURA (PREVENTIVO)

### 1. Política de Contraseñas OWASP ASVS V2.1 y Criptografía
- **MUST (Longitud y Caracteres ASVS V2.1.1–V2.1.3):** Contraseñas de mínimo 12 y máximo 128 caracteres. Permitir todos los caracteres imprimibles Unicode, espacios y emojis. Prohibir reglas arbitrarias de composición que exijan combinaciones forzadas de símbolos si la contraseña supera los 12 caracteres.
- **MUST (Pre-hash SHA-256 para Bcrypt >72 bytes):** Como Bcrypt trunca silenciosamente a 72 bytes, pre-hashear la contraseña con `hashlib.sha256(password.encode("utf-8")).hexdigest()` antes de pasarla a Bcrypt, evitando dependencias externas complejas cuando PyPI no esté disponible.
- **MUST (Rechazo de Contraseña Idéntica):** Bloquear con `400 Bad Request` si la nueva contraseña coincide con la contraseña actual (`verify_password(new_pass, current_hash)`).
- **MUST (Denylist de Contraseñas Filtradas ASVS V2.1.7):** Validar contra denylist local de contraseñas comprometidas y términos de dominio (`admin12345678`, `honeymetrics`, etc.).
- **MUST (CSPRNG Exclusivo):** Prohibido usar `Math.random()` o `random`. Usar siempre `secrets` (Python) y `window.crypto.getRandomValues()` (JS).
- **MUST (Cifrado en Reposo de Semillas MFA):** Toda semilla TOTP (`totp_secret`) debe cifrarse en base de datos usando Fernet o AES-256-GCM.

### 2. Autenticación, MFA Atómico y Recuperación ASVS V2.8
- **MUST (Enjaulado Server-Side de Claves Temporales):** Si `user.must_change_password and settings.REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN` es `True`, `get_current_user` en `deps.py` DEBE bloquear con `403 Forbidden` cualquier petición API hacia recursos operativos, permitiendo únicamente `GET /users/me`, `PUT /users/me/password` y `POST /auth/logout`.
- **MUST (MFA de Uso Único Atómico):** El `mfa_token` (`mfa_pending=True`) debe registrarse en `revoked_tokens` en el primer intento (acierte o falle). Prohibido permitir reintentos con el mismo token.
- **MUST (Reautenticación para Desactivar MFA):** Exigir la contraseña actual (`current_password`) en `POST /users/me/mfa/disable`.
- **MUST (MFA Recovery — 8 Backup Codes ASVS V2.8):** Al activar MFA, generar 8 códigos de respaldo (`XXXX-XXXX`) de un solo uso, almacenar solo su hash SHA-256 en base de datos (`mfa_backup_codes`) y permitir su uso en `/login/mfa-verify`. Proveer endpoint de reset administrativo `POST /users/{id}/mfa/reset` (`admin:all`).
- **MUST (Invalidación Reactiva con `auth_version`):** Todo cambio de clave o reseteo de MFA incrementa `user.auth_version`, invalidando tokens concurrentes pero emitiendo un nuevo JWT para la sesión activa.
- **MUST (Higiene de Sesión en Cliente):** Al iniciar sesión o hacer logout, ejecutar `localStorage.clear()` y `sessionStorage.clear()` antes de persistir las nuevas credenciales para purgar banderas de sesiones anteriores.

### 3. Autorización y Erradicación de Escalación por Subcadena
- **MUST (Coincidencia Exacta de Roles):** Prohibido usar heurísticas como `if "admin" in role.lower(): return ALL_SCOPES`. Exigir coincidencia exacta normalizada contra el mapa canónico de roles.
- **MUST (Anti-IDOR / BOLA):** Todo recurso consultado o borrado por ID debe validar pertenencia (`user_id == current_user.id`) o scope administrativo explícito.
- **MUST (Anti-Auto-Bloqueo de Administrador):** Bloquear con `400 Bad Request` si un administrador intenta auto-desactivarse (`is_active=False`) o auto-degradarse de rol en `PUT /users/{id}`.

### 4. Integridad ML, Deserialización Segura y Resiliencia
- **MUST:** Prohibido usar `joblib.load()` o `pickle.load()` directamente. Usar `safe_joblib_load()` verificando el SHA-256 antes de deserializar.
- **MUST (Sync de Hashes en Reentrenamiento):** Cuando un pipeline reentrene modelos legítimamente (`retrain_pipeline.py`), debe actualizar atómicamente el manifiesto `artifact_hashes.json` antes de invocar `hot_reload()`.
- **MUST (Buffer Flush en Shadow Workers):** Vaciar búferes en memoria (`self._buffer.clear()`) tras escribir en disco para prevenir fugas de memoria $O(N^2)$.
- **MUST (Endpoints ML Fuera del Event Loop):** Definir como `def` síncronos los endpoints de inferencia pesada (para que Starlette los corra en threadpool) e imponer `max_length <= 500` en listas de entrada.

### 5. Validación Canónica de IPs y Red
- **MUST:** Desempaquetar siempre `ip.ipv4_mapped` al validar IPs y rechazar loopback (`127.0.0.1`, `::1`), link-local (`169.254.x.x`), privadas y no globales (`not ip.is_global`).
- **MUST:** En rate limiting, aceptar `CF-Connecting-IP` y `X-Forwarded-For` únicamente si el peer TCP pertenece a `TRUSTED_PROXY_CIDRS`.

### 6. Cero Fuga de Información (HTTP 500) y Webhooks
- **MUST NOT:** Prohibido devolver `str(e)` en respuestas HTTP 500. Retornar mensaje genérico y registrar la traza con `logger.exception()`.
- **MUST (Webhooks):** Validar firma HMAC en tiempo constante y verificar que `str(chat_id) == str(ADMIN_TELEGRAM_CHAT_ID)`.

---

## 🧪 FASE B: SUITE DE VERIFICACIÓN POST-CÓDIGO (RECIBOS RDD)
El agente debe ejecutar y adjuntar la salida real de:
1. `pytest tests/core/ -v` (Pruebas de regresión de seguridad de contraseñas, enjaulado y MFA).
2. `bandit -r app/ -ll -ii` y `pip-audit`.
3. `! grep -rn "str(e)" app/api/` (0 fugas en controladores).
4. `! grep -rn "in normalized" app/core/permissions.py` (0 coincidencias parciales de rol).
