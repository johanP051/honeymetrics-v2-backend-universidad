---
name: clean-architecture-and-code-hygiene
description: >-
  Estándar obligatorio de diseño y escritura de código bajo Clean Architecture (5 capas en Backend)
  y Container / Custom Hooks / Presentational Components (en Frontend). Se aplica SIEMPRE al
  planificar, crear o modificar código fuente.
---

# 🏛️ Clean Architecture, Design Patterns & Code Hygiene Standard

## 1. Backend: Clean Architecture en 5 Capas (Regla de Dependencia)
Las dependencias fluyen estrictamente hacia adentro (`Router -> DTO/Schema -> Service -> Model/ORM -> Core`):

1. **Capa 1 — Presentación / Transporte (`app/api/`):**
   - **Thin Controllers (< 15–20 líneas por función):** Solo reciben el request HTTP, inyectan dependencias (`Depends(get_db)`, `Security(...)`), llaman al servicio y devuelven el DTO.
   - **MUST NOT:** Prohibido escribir consultas ORM (`db.query(...)`, `select(...)`), lógica criptográfica o bucles de negocio en routers.
2. **Capa 2 — Contratos en Frontera (`app/schemas/`):**
   - **Uso Estricto de DTOs (Pydantic v2):** Todo endpoint DEBE declarar `response_model=...` explícito (usar `GenericSuccessResponse` para mutaciones simples).
   - Usar `model_config = ConfigDict(from_attributes=True)`. Prohibido `class Config:` de v1.
   - **MUST NOT:** Prohibido retornar instancias ORM de SQLAlchemy crudas o diccionarios `dict` sin tipar.
3. **Capa 3 — Aplicación y Dominio (`app/services/`):**
   - Contiene el 100% de las reglas de negocio y transacciones. Desacoplado del protocolo HTTP (usar excepciones de dominio en `app/core/domain_errors.py`).
   - **Command-Query Separation (CQS):** Ningún método `GET` puede mutar la base de datos ni ejecutar `db.commit()` ocultos.
4. **Capa 4 — Persistencia y Modelos (`app/models/` y `app/db/`):**
   - **Cero Efectos Secundarios al Importar:** Prohibido `Base.metadata.create_all()` en el ámbito global de `session.py`. Esquema gobernado 100% por **Alembic**.
   - **Prevención de Consultas $N+1$:** Prohibido queries en bucles `for`; usar `joinedload`, `selectinload` o agregaciones SQL.
5. **Capa 5 — Core e Infraestructura (`app/core/`):**
   - Configuración 12-Factor (`config.py`), criptografía (`security.py`), permisos (`permissions.py`) y rate limit (`rate_limit.py`).

## 2. Frontend: Arquitectura por Features, Custom Hooks y Componentes Puros (React 18/19)
1. **Separación Estricta en 4 Niveles:**
   - **Páginas / Containers (`src/pages/`):** Orquestan layout macro y consumen Custom Hooks.
   - **Custom Hooks (`src/hooks/`):** Única capa autorizada para gestionar estado asíncrono y llamar a `src/api/*Api.js`.
   - **Capa de Red (`src/api/client.js` y `*Api.js`):** Cliente Axios unificado con interceptores Bearer y normalizador de errores 422 (`formatApiErrorDetail`).
   - **Componentes Presentacionales (`src/components/`):** Puros y guiados por `props`. Prohibido importar o invocar clientes HTTP dentro de `src/components/` o `src/utils/`.
2. **Principio DRY y Compartición de Estado:**
   - Si dos o más vistas comparten CRUD (ej. `Settings.jsx` y `AdminHub.jsx`), DEBEN usar el mismo hook (`useUsersAdmin`, `useProfileSecurity`).
3. **Higiene y Tamaño de Archivos:**
   - **Regla Innegociable:** Ningún componente o página debe superar las **200 líneas**. Si crece más, modularizar en subcomponentes atómicos (`UserTable.jsx`, `UserModal.jsx`, etc.).
   - Al reemplazar una vista o componente, eliminar en el mismo commit los archivos huérfanos o `*Mock.jsx`.
