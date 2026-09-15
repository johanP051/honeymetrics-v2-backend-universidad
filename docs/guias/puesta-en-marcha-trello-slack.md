# 📋 Guía de Puesta en Marcha: Tablero Trello y Dailies en Slack

> **Navegación:** [← Volver al Índice Central](../README.md) | [← Anterior: Contratos API](../arquitectura/contratos-api-y-json.md) | [Siguiente: Metodología IA →](../metodologia/aprendizaje-guiado-ia.md)

---

## 📑 Tabla de Contenido
1. [El Rol de la Gestión Ágil en la Cátedra](#1-el-rol-de-la-gestión-ágil-en-la-cátedra)
2. [Configuración del Tablero de Trello (Paso a Paso)](#2-configuración-del-tablero-de-trello-paso-a-paso)
3. [Estructura de las Tarjetas de Usuario y Story Points](#3-estructura-de-las-tarjetas-de-usuario-y-story-points)
4. [El Canal de Slack y la Rutina del Daily Scrum](#4-el-canal-de-slack-y-la-rutina-del-daily-scrum)
5. [Evidencias de Trabajo en Equipo para la Sustentación](#5-evidencias-de-trabajo-en-equipo-para-la-sustentación)

---

## 1. El Rol de la Gestión Ágil en la Cátedra

El profesor de Ingeniería de Software enfatizó que la evaluación de los martes califica **tanto el código entregado como la rigurosidad en la metodología Scrum**:
- ¿El equipo tiene un tablero vivo o fue creado 5 minutos antes de la clase?
- ¿Se dividieron el trabajo de forma equitativa?
- ¿Hicieron seguimiento diario (Daily Scrum)?
- ¿Tienen criterios de aceptación claros para cada historia?

---

## 2. Configuración del Tablero de Trello (Paso a Paso)

### 1. Crear el Tablero
- **Nombre sugerido:** `HoneyMetrics v2 — Scrum Universitario`
- **Visibilidad:** Compartido entre Johan Posada y Juan Pablo Fonseca (y enlace público o de lectura para el docente).

### 2. Estructura Oficial de Columnas (Listas)

```text
+-------------------+   +--------------------+   +---------------+   +-------------------+   +--------------------+
|  Product Backlog  |   |  Sprint 1 (To Do)  |   |  In Progress  |   | QA / Code Review  |   |  Done (Sprint 1)   |
| (Todas las épicas)|   | (Compromiso semanal|   | (En desarrollo|   | (En rama QA antes |   | (Cumple Definition |
|                   |   |  hasta el martes)  |   |  activo)      |   |  del martes)      |   |  of Done - DoD)    |
+-------------------+   +--------------------+   +---------------+   +-------------------+   +--------------------+
```

### 3. Sistema de Etiquetas por Color (Labels)
- 🟩 **Backend:** `Verde` (FastAPI, Schemas, Services, DB)
- 🟦 **Frontend:** `Azul` (React, Componentes, Mocks)
- 🟧 **DevOps:** `Naranja` (Docker, Compose, Cloudflare)
- 🟨 **Documentación:** `Amarillo` (MkDocs, Diagramas, SRS)
- 🟥 **Bug / Bloqueo:** `Rojo` (Incidencias críticas)

---

## 3. Estructura de las Tarjetas de Usuario y Story Points

Cada tarjeta en Trello debe seguir la convención:
`[Story Points] Código: Nombre Descriptivo`

### Ejemplo de Tarjeta 1 (US-02):
- **Título:** `[5 pts] US-02: Infraestructura DevOps y Entorno Dockerizado`
- **Miembro Asignado:** `@JohanPosada`
- **Etiquetas:** `DevOps`, `Backend`
- **Descripción:**
  ```markdown
  **Como:** Desarrollador de infraestructura.
  **Quiero:** Un Dockerfile multi-etapa con usuario no privilegiado (appuser) y Compose Overrides.
  **Para:** Que el backend y la BD levanten de forma idéntica en cualquier máquina con un solo comando.

  **Criterios de Aceptación (BDD):**
  - [x] Contenedor ejecuta bajo usuario UID 1001 (appuser).
  - [x] Backend expone puerto 8001 y base de datos 5433 (sin colisiones).
  - [x] Live-reload activo montando la carpeta app/.
  ```

---

## 4. El Canal de Slack y la Rutina del Daily Scrum

Crea un canal en el espacio de trabajo de Slack llamado **`#honeymetrics-daily`**.

### Regla del Daily:
Cada mañana o al inicio de la sesión de trabajo conjunto, cada miembro envía un mensaje respondiendo las 3 preguntas clave del marco ágil:

```text
📅 Daily Scrum — Sprint 1 — [Día/Mes/Año]
👤 Desarrollador: @JohanPosada / @JuanPabloFonseca

1. ¿Qué completé desde el último daily?
   - Configuré los Compose Overrides desacoplando puertos para evitar colisiones.
   - Creé el DTO de salud y el Thin Controller en /api/v1/endpoints/health.py.

2. ¿Qué planeo completar hoy?
   - Implementar la suite de pruebas unitarias con Pytest en tests/unit/test_health.py.
   - Sincronizar los Mocks en el Frontend con Juan Pablo.

3. ¿Tengo algún obstáculo o bloqueo?
   - Ninguno. La base de datos SQLite y Postgres en Docker corren sin fricción.
```

---

## 5. Evidencias de Trabajo en Equipo para la Sustentación

Para la sustentación de cada martes:
1. **Abrir el Tablero de Trello:** Mostrar cómo las tarjetas del Sprint 1 pasaron de `To Do` $\to$ `In Progress` $\to$ `Done`.
2. **Mostrar el Canal de Slack:** Demostrar que hubo comunicación continua y seguimiento ágil entre Johan y Juan Pablo.
3. **Mostrar el Historial de Git:** Evidenciar que los commits en `develop` fueron realizados por ambos autores mediante co-autoría (`Co-authored-by`).

---

> **Navegación:** [← Volver al Índice Central](../README.md) | [← Anterior: Contratos API](../arquitectura/contratos-api-y-json.md) | [Siguiente: Metodología IA →](../metodologia/aprendizaje-guiado-ia.md)
