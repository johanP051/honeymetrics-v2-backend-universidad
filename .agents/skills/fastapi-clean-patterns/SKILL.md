---
name: fastapi-clean-patterns
description: >-
  Skill maestra de desarrollo en FastAPI para HoneyMetrics Backend. Gobierna el Service Layer Pattern,
  validación estricta con Pydantic v2, endpoints asíncronos, suite de Pytest y configuración 12-Factor.
---

# ⚡ FastAPI Clean Architecture Standards (HoneyMetrics Backend)

Esta Skill define los estándares de código para el backend de **HoneyMetrics 2.0**. Todo desarrollador o agente de IA que trabaje en este repositorio debe cumplir estas normas.

---

## 1. 🏗️ Service Layer Pattern Obligatorio
- **Thin Routers:** Las funciones en `app/api/v1/endpoints/` **NO** deben superar **15 líneas de código**. Solo reciben la petición, delegan en el Service y retornan el Schema.
- **Fat Services:** Toda la lógica de negocio, cálculos de Threat Score, consultas a BD o agregaciones CTI viven en `app/services/`.

```python
# ✅ CORRECTO: Endpoint limpio y declarativo
@router.get("/threats/summary", response_model=ThreatSummarySchema)
async def get_threat_summary() -> ThreatSummarySchema:
    """Retorna el resumen consolidado de amenazas CTI."""
    return ThreatService.get_threat_summary()
```

---

## 2. 🛡️ Validación Estricta con Pydantic v2 (DTOs)
- Todo endpoint debe tener definido su `response_model` y validar entradas con modelos en `app/schemas/`.
- Usar tipos nativos y validadores de campo (`@field_validator`).
- Configuración recomendada para ORM: `model_config = ConfigDict(from_attributes=True)`.
- Cero respuestas con diccionarios Python genéricos sin tipar.

---

## 3. 🧪 Testing Obligatorio con Pytest
- Cada nuevo endpoint en `app/api/v1/endpoints/` debe contar con su archivo de prueba correspondiente en `tests/api/v1/test_<modulo>.py`.
- Usar el fixture `client` definido en `tests/conftest.py`.
- Ningún PR se aprueba si no hay cobertura verde.
- Comando obligatorio de validación local: `pytest --cov=app --cov-report=term-missing --cov-fail-under=80`.

---

## 4. ⚙️ Configuración 12-Factor
- Toda variable se define en `app/core/config.py` mediante `pydantic-settings`.
- Cero IPs, credenciales o URLs quemadas en el código fuente.

---

## 5. 🚨 Resiliencia y Manejo de Errores (NUEVO)
- **Prohibición Total:** El uso de `except Exception: pass` queda ESTRICTAMENTE PROHIBIDO (Error Silencing).
- **Manejo de Excepciones:** Todo error esperado debe usar la clase nativa `HTTPException` de FastAPI para asegurar códigos de estado HTTP correctos.
  ```python
  # ✅ CORRECTO
  try:
      # logica...
  except ItemNotFoundException as e:
      raise HTTPException(status_code=404, detail=str(e))
  ```
- **Concurrencia de Base de Datos:** Toda operación de actualización (UPDATE) sobre registros críticos (Ej: alertas, usuarios) **debe** utilizar bloqueo pesimista en SQLAlchemy mediante `select_for_update()` para evitar race conditions.

---

## 6. 🔒 Seguridad y Prevención SAST (NUEVO)
- Queda totalmente prohibido el hardcoding de contraseñas, tokens JWT, o claves en el código fuente (Ej: en `config.py`).
- Todo secreto DEBE cargarse exclusivamente a través del `.env` y el valor por defecto en los settings de Pydantic debe ser `""` (vacío) o nulo.
- Antes de cada commit, validar fuga de credenciales ejecutando: `grep -rn "password" app/ --include="*.py"` (debe salir limpio).

---

## 7. 🚦 Policy de PR y Gates CI (NUEVO)
- Estructura de pruebas espejo: Todo archivo en `app/api/v1/endpoints/nombre.py` debe tener su reflejo en `tests/api/v1/test_nombre.py`.
- Ningún Pull Request (PR) se mergea a la rama `main` sin superar el **80% de cobertura de código**.
