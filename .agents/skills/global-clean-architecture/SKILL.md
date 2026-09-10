---
name: global-clean-architecture
description: >-
  Estándar global de Arquitectura Limpia, Service Layer Pattern, DTOs con Pydantic/Serializers
  y principios SOLID para cualquier backend (FastAPI, Django, Express, Spring Boot) y frontend (React, Vue).
---

# 🏛️ Global Clean Architecture & Design Patterns

Esta Skill aplica a **todos** los proyectos de desarrollo de software del usuario.

## 1. Regla de Oro: Thin Controllers / Routers, Fat Services
- Los endpoints, routers o controladores **NUNCA** deben contener lógica de negocio, procesamiento de datos, cálculos matemáticos o llamadas complejas a bases de datos/APIs externas.
- Tamaño máximo por endpoint: **15 líneas de código**.
- Flujo obligatorio:
  `HTTP Request` ➔ `DTO/Schema Validation` ➔ `Service Layer` ➔ `Repository / Model` ➔ `Response DTO`

## 2. DTOs y Validación en los Límites (Fail Fast)
- Toda entrada del cliente debe validarse mediante esquemas estrictos (Pydantic en FastAPI, Serializers en DRF, Zod en TypeScript).
- Nunca confiar en los datos del frontend sin validación en el servidor.

## 3. SOLID & DRY
- **Single Responsibility (S):** Cada módulo, clase y archivo cumple una sola función.
- **Dependency Inversion (D):** Programar contra interfaces/abstracciones.
- **Don't Repeat Yourself (DRY):** Extraer funciones reutilizables a `utils/` o Custom Hooks en frontend.

## 4. 12-Factor App (Cero Secretos en Código)
- Prohibido hardcodear URLs, IPs, puertos o contraseñas en el código fuente.
- Toda configuración sensible se gestiona exclusivamente mediante variables de entorno (`.env`).

## 5. 🏷️ Namespacing Estricto (Prevención de Colisiones)
### A. En Django (Monolitos / DRF):
- **Templates:** Deben llevar obligatoriamente la subcarpeta con el nombre de la app (ej. `templates/logsApp/dashboard.html` y renderizar `render(request, "logsApp/dashboard.html")`). Prohibido renderizar sin namespace (`"dashboard.html"`).
- **URLs:** Definir siempre `app_name = "nombre_app"` en `urls.py` para invocar rutas como `reverse("logsApp:dashboard")`.

### B. En Arquitecturas Desacopladas (FastAPI + React):
- **API Router Namespacing:** Cada dominio/módulo debe incluirse con su prefijo y tag en el router central (`api_router.include_router(threats.router, prefix="/threats", tags=["Threat Intelligence"])`) bajo el versionamiento global `/api/v1`.
- **Frontend Components & Assets:** Componentes organizados por dominio (`components/threats/`, `components/auth/`) para evitar colisiones de nombres genéricos como `Card` o `Modal`.
