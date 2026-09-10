---
name: arquitectura-desacoplada
trigger: always_on
description: Reglas estrictas para mantener la separación entre el Frontend y el Backend en el repositorio, usando Nginx y repos independientes.
---

# 🏗️ Regla de Arquitectura Desacoplada (API-First)

Para el desarrollo del proyecto HoneyMetrics, el Agente debe hacer cumplir **estrictamente** las siguientes normas de arquitectura, inspiradas en las mejores prácticas de infraestructura moderna (DevOps):

1. **Cero Monolitos:** Prohibido el uso de Django Templates (`render()`, `TemplateResponse`) para la UI de usuario final. Django **solo** actuará como un proveedor de API JSON/REST.
2. **Repositorios Aislados:** El código del Frontend (React, Angular, Vue) nunca debe mezclarse en este mismo repositorio. Si el usuario intenta agregar código frontend a este repositorio, el agente debe detenerlo y recordarle clonar o inicializar un repositorio separado.
3. **Manejo de CORS y Nginx:**
   - La comunicación entre Frontend y Backend en producción se gestionará a través de un proxy reverso (Nginx).
   - Nginx servirá los archivos estáticos de la Single Page Application (SPA) en la raíz (`/`) y hará proxy a Django exclusivamente en las rutas `/api/` y `/admin/`.
4. **Despliegue Seguro (Docker):**
   - El entorno de Docker usará Dockerfiles Multi-etapa (Builder pattern).
   - El proceso de Django se ejecutará bajo un usuario sin privilegios (`non-root`) dentro del contenedor.
   - Las bases de datos y otros servicios internos JAMÁS expondrán puertos al host en los archivos `docker-compose.prod.yml` (ej. mapeos como `1435:1433` quedan estrictamente prohibidos).
5. **Autenticación Desacoplada:** Reemplazar el uso de `SessionAuthentication` clásico de Django por `JWT (JSON Web Tokens)` mediante `djangorestframework-simplejwt` u otro proveedor stateless, para permitir el consumo seguro desde el frontend.
