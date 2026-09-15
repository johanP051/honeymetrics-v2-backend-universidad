---
name: arquitectura-desacoplada
trigger: always_on
description: Reglas estrictas para mantener la separación entre el Frontend y el Backend en el repositorio, usando Nginx, Docker seguro y seguridad PoLP en Base de Datos.
---

# 🏗️ Regla de Arquitectura Desacoplada (API-First) & Seguridad de Datos

Para el desarrollo del proyecto HoneyMetrics, el Agente debe hacer cumplir **estrictamente** las siguientes normas de arquitectura, inspiradas en las mejores prácticas de infraestructura moderna (DevOps):

1. **Cero Monolitos:** Prohibido el uso de Django Templates (`render()`, `TemplateResponse`) para la UI de usuario final. El backend **solo** actuará como un proveedor de API JSON/REST.
2. **Repositorios Aislados:** El código del Frontend (React, Angular, Vue) nunca debe mezclarse en este mismo repositorio. Si el usuario intenta agregar código frontend a este repositorio, el agente debe detenerlo y recordarle clonar o inicializar un repositorio separado.
3. **Manejo de CORS y Nginx:**
   - La comunicación entre Frontend y Backend en producción se gestionará a través de un proxy reverso (Nginx).
   - Nginx servirá los archivos estáticos de la Single Page Application (SPA) en la raíz (`/`) y hará proxy al backend exclusivamente en las rutas `/api/` y `/admin/`.
4. **Despliegue Seguro (Docker):**
   - El entorno de Docker usará Dockerfiles Multi-etapa (Builder pattern).
   - El proceso de backend se ejecutará bajo un usuario sin privilegios (`non-root`, UID 1001 / `appuser`) dentro del contenedor.
   - Las bases de datos y otros servicios internos JAMÁS expondrán puertos al host en los archivos `docker-compose.prod.yml` (ej. mapeos como `1435:1433` o `5432:5432` quedan estrictamente prohibidos).
5. **Autenticación Desacoplada:** Reemplazar el uso de sesiones monolíticas clásicas por `JWT (JSON Web Tokens)` stateless mediante PyJWT o SimpleJWT, para permitir el consumo seguro desde el frontend.
6. **Seguridad de Base de Datos en Producción (Principio de Menor Privilegio - PoLP):**
   - **Regla de Oro:** *"1 App = 1 Usuario Dedicado"*.
   - En entornos de producción (`docker-compose.prod.yml` y `.env` productivo), está **estrictamente prohibido** conectar la aplicación utilizando superusuarios de motor (`sa`, `root` o `postgres`).
   - La conexión de producción debe utilizar obligatoriamente un usuario enjaulado (ej. `usr_honeymetrics`) con permisos acotados exclusivamente a su base de datos (`ALTER ROLE db_owner` en SQL Server, `GRANT ALL PRIVILEGES ON DATABASE` en PostgreSQL).
   - En desarrollo local se permite flexibilidad con credenciales de prueba, pero el agente debe auditar y advertir si se detectan superusuarios configurados en perfiles o scripts de despliegue productivo.
