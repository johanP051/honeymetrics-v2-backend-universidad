---
name: global-resilience-error-prevention
description: >-
  Estándar global de Resiliencia, Manejo Robusto de Excepciones, Prevención de Race Conditions,
  Transacciones Atómicas, Idempotencia, Timeouts y Políticas de Reintento (Retry Backoff).
---

# 🛡️ Global Resilience, Concurrency & Error Prevention Standard

Esta Skill gobierna la robustez del código en cualquier lenguaje (Python/Django/FastAPI, JavaScript/React, Node, Go) para prevenir caídas silenciosas, condiciones de carrera (*Race Conditions*) y corrupción de datos.

---

## 1. Prevención de Race Conditions y Concurrencia
Cuando múltiples usuarios, hilos o workers de Celery acceden al mismo registro simultáneamente:

### A. Bloqueo Pesimista en Base de Datos (`select_for_update`)
- **Regla:** Si lees un valor para actualizarlo basándote en su valor previo (ej. sumar intentos de login, decrementar stock, actualizar balance), es **OBLIGATORIO** usar bloqueo a nivel de fila dentro de una transacción atómica:
```python
# ✅ CORRECTO (Bloqueo de fila para evitar Race Condition)
from django.db import transaction

with transaction.atomic():
    threat = AttackerIP.objects.select_for_update().get(ip="164.92.141.248")
    threat.total_events += 1
    threat.threat_score = calculate_score(threat.total_events)
    threat.save()
```

### B. Idempotencia en APIs y Tareas Asíncronas
- Toda operación `POST`/`PUT` sensible o tarea en background debe ser idempotente usando una clave única (`Idempotency-Key` en headers o token de transacción) para evitar duplicados si la red reintenta la petición.

---

## 2. Manejo Estricto de Excepciones (No Silent Failures)

### A. Prohibición de Excepciones Genéricas Desnudas
- ❌ **PROHIBIDO:** `try: ... except: pass` o `try: ... except Exception: pass` (oculta bugs catastróficos).
- ✅ **OBLIGATORIO:** Capturar excepciones específicas y registrar el contexto:
```python
# ❌ PROHIBIDO
try:
    data = requests.get(url).json()
except:
    pass

# ✅ CORRECTO
import logging
logger = logging.getLogger(__name__)

try:
    response = requests.get(url, timeout=5.0)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.Timeout:
    logger.warning("Timeout consultando servicio externo: %s", url)
    data = get_cached_fallback()
except requests.exceptions.HTTPError as err:
    logger.error("Error HTTP %s al consultar %s", err.response.status_code, url)
    raise ExternalServiceException("Servicio de telemetría no disponible") from err
```

---

## 3. Timeouts y Circuit Breakers en Red Externa
1. **Timeouts Obligatorios:** Toda llamada HTTP/Socket externa debe tener timeout explícito (ej. `timeout=(3.0, 10.0)` — 3s conexión, 10s lectura). Cero peticiones indefinidas.
2. **Exponential Backoff:** Los reintentos de tareas (ej. Celery / APIs) deben espaciarse exponencialmente (`2s, 4s, 8s, 16s...`) con jitter aleatorio para no saturar el servicio caído.

---

## 4. Manejo de Errores en Frontend (React Error Boundaries)
- Ningún fallo en un componente de visualización (ej. gráfico Plotly o tabla) debe tumbar toda la aplicación (*White Screen of Death*).
- Toda vista debe contar con `ErrorBoundary` y componentes de estado visual: `LoadingState`, `EmptyState` y `ErrorFallbackState` con botón de "Reintentar".
