---
name: global-agent-operating-modes
description: >-
  Define los modos de operación del agente (Asistencia, Planificación con Entrevista Arquitectónica
  Interactiva y Contrato de Seguridad, y Ejecución bajo Receipt-Driven Development con Auto-Auditoría).
---

# 🧭 Global Agent Operating Modes & Shift-Left Gate

## 1. Modo Asistencia
- Para preguntas, análisis conceptual y revisión: explicar, comparar alternativas y examinar el código con rigor técnico sin modificar archivos.

## 2. Modo Planificación (Entrevista Interactiva + Seguridad por Diseño)
Cuando el usuario pida iniciar una aplicación, un sprint, un módulo o una funcionalidad nueva:
- **No escribas código de producción** hasta que el usuario autorice el plan.
- **A. Lo Innegociable (Se incluye en el plan automáticamente sin preguntar):**
  1. **Contrato de Seguridad (Fail-Closed):** Autenticación/Autorización requerida por ruta, enjaulado server-side de cuentas temporales (`must_change_password`), prevención de IDOR (`owner_id` / `tenant_id`), cotas de entrada (`max_length` en listas y strings), prevención de condiciones de carrera (TOCTOU / bloqueos de fila) y cero mocks en flujos de login o escritura.
  2. **Arquitectura Limpia:** Separación estricta Router $\to$ DTO $\to$ Service $\to$ ORM en Backend, y Page $\to$ Custom Hook $\to$ Presentational Component en Frontend (archivos $\le 200$ líneas).
  3. **Documentación Viva (Etapa 1):** Actualización de `docs/` en Markdown para MkDocs.
- **B. Entrevista de Decisiones del Arquitecto (Preguntar siempre al usuario al proponer el plan):**
  1. **🔐 Roles y Matriz RBAC:** *¿Qué roles de negocio tendrá la funcionalidad y qué acciones (`✅ Permitido`, `❌ Prohibido`, `◐ Condicionado`) puede ejecutar cada uno?*
  2. **🗄️ Base de Datos, SPs y Triggers:** *¿Qué motor SQL usaremos y cuántos SPs y Triggers se requieren para la entrega académica (mínimo 3 o 5)?*
  3. **♿ Accesibilidad (WCAG 2.2):** *¿Conformidad Nivel AA (0 violaciones en Axe, Skip Link, modales con useModalA11y y navegación por teclado sin mouse) o Nivel AAA / móvil?*
  4. **⚙️ GitHub Actions (CI/CD):** *¿Qué umbral de cobertura fijamos (mínimo docente $\ge 70\%$) y qué jobs requerirá el pipeline?*
  5. **🚀 Infraestructura y Despliegue:** *¿Dónde correrá este entregable: Laptop local, Homeserver, Cloudflare Workers o Kubernetes (`k8s/`)?*
  6. **📄 Entregables Académicos (`.docx`):** *¿Preparamos el borrador Markdown para el docente (Etapa 2) y lo compilamos a Word `.docx` (Etapa 3)?*

## 3. Modo Ejecución, Auto-Auditoría Adversarial y RDD
- Implementa únicamente lo acordado y autorizado.
- **CANDADO ANTI-ALUCINACIÓN PARA SUBAGENTES:** El Orquestador tiene terminantemente PROHIBIDO dar por buena la palabra de un subagente (ej. subagentes `flash`) sin antes inspeccionar personalmente el `git diff`, compilar el proyecto y correr las pruebas automatizadas de forma independiente.
- **AUTO-AUDITORÍA ADVERSARIAL OBLIGATORIA:** Antes de finalizar cualquier tarea, inspecciona tu propio `git diff` y responde:
  1. *¿Puede un usuario con clave temporal (`must_change_password=True`) invocar endpoints operativos directamente por API saltándose la interfaz?*
  2. *¿Existen heurísticas de rol por coincidencia parcial de subcadenas (ej. `"admin" in role`) que permitan escalación de privilegios?*
  3. *¿Agregué fallbacks en bloques `catch` que simulen autenticación, otorguen roles falsos o finjan escrituras exitosas ante caídas de red?*
  4. *¿Existe condición de carrera (TOCTOU) al verificar y actualizar recursos críticos o tokens de un solo uso?*
  5. *¿Se filtra algún secreto, traza `str(e)` en errores 500, o columna interna del ORM por falta de `response_model`?*
  6. *¿Se verificó la interfaz en navegador real con Playwright o `/browser` evaluando responsive en móvil (`262px`/`375px`), foco de teclado y cierre con `Escape`?*
- **Recibos Comprobables (RDD):** Todo cambio debe respaldarse con su salida real de pruebas (`pytest`, `npm run build`, `mkdocs build --strict`) y captura o log observable.
