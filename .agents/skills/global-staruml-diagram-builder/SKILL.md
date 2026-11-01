---
name: global-staruml-diagram-builder
description: >
  Skill maestra para extraer, auditar, reparar y generar diagramas UML en StarUML
  (Casos de Uso, Secuencia, Actividades, Clases y MER) vía REST API y manipulación
  directa del AST (.mdj). Incluye el estándar académico Gualivá/UDEC, exportación
  masiva SVG/PNG y auto-auditoría visual en loop (PDF -> pdftoppm -> view_file).
---

# Skill: global-staruml-diagram-builder (v2.0)

## 🎯 Modos de Uso Rápido (Comandos Naturales del Usuario)

Cuando el usuario pida cualquiera de estas tareas, ejecuta el flujo indicado sin hacer preguntas innecesarias:

1. **"Extrae los diagramas de `<archivo.mdj>` a `<carpeta>`"**:
   Ejecuta directamente el script oficial de extracción:
   ```bash
   python3 /home/sebas/.gemini/config/skills/global-staruml-diagram-builder/scripts/staruml_export_all.py "<ruta_mdj>" "<carpeta_destino>"
   ```
2. **"Audita o repara los errores del archivo `<archivo.mdj>`"**:
   Ejecuta el auditor/reparador AST sobre una copia de seguridad:
   ```bash
   python3 /home/sebas/.gemini/config/skills/global-staruml-diagram-builder/scripts/staruml_audit_and_patch_mdj.py "<ruta_mdj>" --patch
   ```
3. **"Compila los diagramas en un Markdown y PDF sin cortes"**:
   Ejecuta el pipeline de consolidación + renderizado Chrome Headless + verificación visual con `pdftoppm` y `view_file` (Sección 6).

---

## 🏛️ 1. Estándar Académico Inquebrantable (Patrón Gualivá — UDEC)

Todo diagrama para entrega universitaria o sustentación DEBE cumplir estas reglas sin excepción:

### 1.1 Reglas de Diagramas de Secuencia (`UMLSequenceDiagram`)
1. **Las 5 Líneas de Vida Canónicas Fijas (Obligatorio):**
   $$\text{Actor (Usuario / Administrador / Rol)} \longrightarrow \text{Vista} \longrightarrow \text{Controlador} \longrightarrow \text{Modelo} \longrightarrow \text{BaseDeDatos}$$
   * **PROHIBIDO** inventar líneas de vida técnicas como `Frontend`, `AuthRouter`, `Schema/DTO`, `Service`, `Repository`, `MISP`, `Wazuh` o `Telegram`. Las integraciones externas se modelan como llamadas internas (self-calls) del `Modelo`.
2. **Cero Código, Cero Endpoints HTTP y Cero SQL en las Flechas:**
   * **PROHIBIDO** escribir `GET /api/v1/...`, `POST /api/...`, `PUT`, `DELETE`, `HTTP 200 OK`, `SELECT * FROM` o `UPDATE tabla SET...` en los nombres de los mensajes.
   * Usar exclusivamente frases de dominio en español:
     - `Vista -> Controlador`: `Solicitar interfaz de...`, `Solicitar formulario de...`, `Solicitar creación/actualización/eliminación de...`
     - `Controlador -> Controlador` (self-call): `Procesar solicitud`, `Validar campos del formulario`, `Validar permisos de [Rol]`
     - `Controlador -> Modelo`: `Servicio de [Acción]` o `Llama a servicio de [Acción]`
     - `Modelo -> BaseDeDatos`: `Consultar [Entidad] registrada`, `Consultar registro por ID`, `Almacenar [Entidad]`, `Actualizar estado de [Entidad]`
     - `Vista -> Actor`: `Mostrar mensaje "..."` (con el texto exacto entre comillas).
3. **Ciclos Cortos de Activación (No barras infinitas):**
   * En el `Controlador`, el ciclo de pedir una vista o formulario debe cerrar su rectángulo de activación al responder `Redirigir a...`. El envío posterior del formulario abre un nuevo rectángulo de activación separado.
4. **Marcos de Precondición `ref` (`UMLInteractionUse`):**
   * Todo diagrama posterior al login inicia arriba con un marco `ref` que abarca las 5 líneas de vida.
   * En diagramas de **Consultar** o **Crear**: el `ref` apunta a `IniciarSesión` (ej. `RF01 Autenticación MFA v2`).
   * En diagramas de **Actualizar/Editar** y **Eliminar**: el `ref` apunta OBLIGATORIAMENTE al diagrama de **`Consultar [Módulo]`** correspondiente (ej. `RF03 Consultar Lista Negra IP` o `RF06 Consultar Usuarios`).
   * **Prohibido dejar cuadros `ref` en blanco:** En el `.mdj`, el `UMLInteractionUse` debe tener `refersTo` vinculado al `_id` del `UMLInteraction` destino Y su `nameLabel` subView debe tener `"text"` poblado y `"visible": true`.
5. **Consulta Previa Obligatoria en Eliminación:**
   * En todo diagrama de Eliminar, antes de inactivar o borrar en `BaseDeDatos`, el `Modelo` DEBE hacer primero `Consultar registro activo por ID` $\to$ `Retornar registro encontrado`, mostrar el modal de confirmación y solo entonces ejecutar la baja.
6. **Fragmentos `alt` y `opt` (`UMLCombinedFragment`) sin el bug `alt alt`:**
   * Para evitar que StarUML dibuje `alt alt` en la pestaña pentagonal, el `UMLCombinedFragment` debe tener `"interactionOperator": "alt"` y `"name": ""` (vacío) o una pregunta corta (ej. `"¿Credenciales válidas?"`), NUNCA `"name": "alt"`.
   * Las condiciones de cada rama (`UMLInteractionOperand`) se colocan en la propiedad `"guard"` sin corchetes (StarUML agrega `[` `]` automáticamente) y la vista `UMLInteractionOperandView` debe ajustar su `"height"` para coincidir con el último mensaje de esa rama.
7. **Numeración Continua Post-`ref` (Calibración Gualivá):**
   * Desactivar `"showSequenceNumber": false` en StarUML (`"showSequenceNumber": true` o numeración de mensajes explícita) para garantizar la continuidad secuencial a través de los casos de uso encadenados: los números no se reinician en 1 tras un marco `ref`, sino que continúan la secuencia lógica del flujo (`1..19` en Login $\to$ `20..28` tras `ref: RF01` $\to$ `29..48` tras `ref: Consultar`).

### 1.2 Reglas de Diagramas de Casos de Uso (`UMLUseCaseDiagram`)
1. **Triple Frontera Visual:**
   * Marco exterior `uc [Código - Nombre]`, caja interior `Sistema` (o `Sistema HoneyMetrics`), y actores situados **fuera** de la caja `Sistema` pero dentro del marco exterior.
2. **Nombres Canónicos de Actores:**
   * Usar exactamente los nombres oficiales de los roles del sistema (`Superusuario`, `Analista de datos`, `Consultor de Ciberseguridad`, `Directivo de T.I.`). **PROHIBIDO** usar `Administrador`.
3. **El Patrón CRUD Jerárquico (Regla Gualivá):**
   * Las operaciones **`Actualizar / Editar / Modificar`** y **`Eliminar / Desactivar`** **SIEMPRE** se conectan mediante `«extend»` apuntando hacia **`Consultar [Entidad]`** (jamás se conectan como óvalos sueltos directo al actor sin extender de Consultar).
   * Todos los casos de uso comienzan con un **verbo en infinitivo** (`Consultar`, `Registrar`, `Modificar`, `Eliminar`, `Validar`).
4. **Tabla Descriptiva Obligatoria debajo de cada Figura:**
   * En los documentos Markdown/Word, inmediatamente debajo de cada figura de Caso de Uso debe ir su tabla descriptiva (`Caso de Uso | Actor(es) | Descripción`), iniciando cada fila con la fórmula canónica:
     - *"Caso de uso base, donde el [rol]..."*
     - *"Es un incluido de [Caso Base], donde el sistema..."*
     - *"Extiende a [Caso Base], permitiendo al [rol]..."*

### 1.3 Reglas de Diagramas de Actividades (`UMLActivityDiagram`)
1. **Enfoque 100% Gerencial (Cero Tecnicismos):**
   * Diseñados para que un gerente o cliente entienda el proceso de negocio. Prohibido mencionar `HTTP 200`, `HTTP 400`, `POST`, `GET`, `JWT`, `DTO`, `SQL` o `Endpoint`.
2. **Exactamente 2 Calles (`UMLActivityPartition`):**
   * Calle Izquierda ($X \in [80, 420]$, centro $X = 250$): **Actor / Rol Humano**.
   * Calle Derecha ($X \in [420, 780]$, centro $X = 600$): **Sistema HoneyMetrics**.
3. **Nodos Inicial y Final en el Actor y Mensajes Literales:**
   * El nodo inicial ($\bullet$) y los nodos finales ($\odot$) van siempre en el carril izquierdo (Actor).
   * Todo flujo cierra con el Sistema ejecutando `Generar/Mostrar mensaje "TEXTO EXACTO"` y el Actor ejecutando `Visualizar mensaje "TEXTO EXACTO"`.
4. **Prohibición de Clones en Eliminación:**
   * El diagrama de actividad de `Eliminar` jamás debe hablar de "formulario de actualización". Debe modelar: *Buscar registro $\to$ Verificar existencia $\to$ Solicitar confirmación en modal $\to$ Decisión `[Acepta / Cancela]` $\to$ Inactivar/Eliminar registro*.
5. **Geometría Anti-Cruces:**
   * Todas las `UMLActionView` llevan `"wordWrap": true`, `width: 160`, `height: 65`.
   * Las bifurcaciones que esquivan bloques intermedios usan el canal ortogonal lateral derecho ($X = 720$) indexado por tupla `(source_node_id, target_node_id)`.

### 1.4 Reglas de MER (Modelo Entidad-Relación) y Diagrama de Clases (Calibración Gualivá)
1. **Generación Unificada en Proporción Vertical (Portrait) en PlantUML:**
   * Generar **exactamente 1 solo MER y 1 solo Diagrama de Clases** consolidados en PlantUML / StarUML en orientación vertical (Portrait) con fondo blanco limpio (`skinparam backgroundColor white`), optimizados para hoja tamaño carta en documentos formales y sin fragmentaciones.
2. **Cero Tablas "Isla" Desconectadas:**
   * Todas y cada una de las entidades y tablas deben contar con al menos una relación de cardinalidad explícita conectada al grafo relacional del dominio (FKs / dependencias); queda terminantemente prohibido dejar entidades huérfanas o tablas desconectadas.

---

## 🔌 2. Catálogo Completo de Endpoints REST de StarUML (`localhost:12345/api`)

Header obligatorio: `{"Authorization": "Bearer secret", "Content-Type": "application/json"}`

### 2.1 Proyecto y Exportación General
* `GET  /api/status` — Estado del servidor y rutas activas.
* `POST /api/project/open` — `{"path": "/ruta/absoluta/archivo.mdj"}`
* `POST /api/project/save` — `{"path": "/ruta/absoluta/archivo.mdj"}`
* `POST /api/diagrams/{id_url_encoded}/export` — `{"format": "png"}` o `{"format": "svg"}` $\to$ devuelve contenido en `resp["data"]["file"]["content"]`.
* `GET  /api/elements/{id_url_encoded}/views` — Obtiene las vistas asociadas a un elemento.
* `PUT  /api/views/{viewId_url_encoded}` — Modifica propiedades visuales (`left`, `top`, `width`, `height`, `wordWrap`, `containerExt`).

### 2.2 Casos de Uso (`/api/usecase/...`)
* `POST /api/usecase/diagrams` — `{"name": "..."}`
* `POST /api/usecase/subjects` — `{"name": "...", "diagramId": d, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`
* `POST /api/usecase/actors` — `{"name": "...", "diagramId": d, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`
* `POST /api/usecase/use-cases` — `{"name": "...", "diagramId": d, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`
* `POST /api/usecase/associations` — `{"diagramId": d, "sourceId": a, "targetId": b}`
* `POST /api/usecase/includes` — `{"diagramId": d, "sourceId": base_uc, "targetId": included_uc}`
* `POST /api/usecase/extends` — `{"diagramId": d, "sourceId": extending_uc, "targetId": base_uc}` *(¡Ojo! En UML `sourceId` es el hijo que extiende y `targetId` es el caso base `Consultar`)*.
* `POST /api/usecase/generalizations` — `{"diagramId": d, "sourceId": child_actor, "targetId": parent_actor}`

### 2.3 Secuencia (`/api/seq/...`)
* `POST /api/seq/interactions` — `{"name": "..."}`
* `POST /api/seq/diagrams` — `{"parentId": inter_id, "name": "..."}`
* `POST /api/seq/interactions/{inter_id_enc}/lifelines` — `{"name": "...", "diagramId": d, "x": x, "y": 50}`
* `POST /api/seq/interactions/{inter_id_enc}/messages` — `{"name": "...", "source": src_ll, "target": tgt_ll, "messageSort": "synchCall"|"reply", "diagramId": d, "y": y, "activationHeight": h}`
* `POST /api/seq/interactions/{inter_id_enc}/interaction-uses` — `{"name": "...", "refersTo": target_inter_id, "diagramId": d, "x": 80, "y": y, "width": 1100, "height": 60}`
* `POST /api/seq/interactions/{inter_id_enc}/combined-fragments` — `{"name": "", "interactionOperator": "alt"|"opt", "diagramId": d, "x": 50, "y": y, "width": 1150, "height": h}`
* `POST /api/seq/combined-fragments/{cf_id_enc}/operands` — `{"name": "", "guard": "Condición == false"}`

### 2.4 Actividades (`/api/activity/...`)
* `POST /api/activity/diagrams` — `{"name": "..."}`
* `POST /api/activity/partitions` — `{"name": "...", "diagramId": d, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`
* `POST /api/activity/actions` — `{"name": "...", "diagramId": d, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`
* `POST /api/activity/control-nodes` — `{"kind": "initial"|"activityFinal"|"decision", "diagramId": d, "x": x, "y": y}`
* `POST /api/activity/control-flows` — `{"diagramId": d, "sourceId": a, "targetId": b, "guard": "Sí"}`

---

## 🔄 3. Loop Obligatorio de Auto-Auditoría antes de Entregar al Usuario (RDD)

Prohibido entregar un Markdown o PDF al usuario sin haber ejecutado este ciclo cerrado:

1. **Auditoría AST sobre el `.mdj`:**
   Ejecutar `staruml_audit_and_patch_mdj.py` y verificar **0 errores** de:
   - Marcos `ref` con texto vacío.
   - Fragmentos con etiqueta duplicada `alt alt`.
   - Mensajes de secuencia con `GET /`, `POST /`, `PUT /`, `DELETE /` o `UPDATE ... SET`.
   - Actores con nombres no canónicos (según Sección 1.2.2, exigir `Superusuario`, `Analista de datos`, `Consultor de Ciberseguridad`, `Directivo de T.I.`; prohibido usar `Administrador` en los diagramas UML).
   - Diagramas de eliminar que contengan texto de actualización.
2. **Exportación Limpia:**
   Ejecutar `staruml_export_all.py` para generar SVGs (con `viewBox` inyectado) y PNGs en alta resolución con nombres ASCII limpios (sin espacios ni `%20`).
3. **Compilación Oficial a PDF siempre con `compilar_pdf.sh` y `--no-pdf-header-footer`:**
   - Usar obligatoriamente el script autónomo de compilación de 2 etapas `compilar_pdf.sh`:
     - **Etapa 1:** Generación de HTML intermedio estructurado con Pandoc:
       ```bash
       pandoc -f markdown-implicit_figures -s --metadata title="Diagramas UML" "$MD_FILE" -o "$HTML_PREVIEW"
       ```
     - **Etapa 2:** Renderizado a PDF con Google Chrome / Chromium en modo headless sin bordes ni encabezados/pies residuales del navegador:
       ```bash
       google-chrome --headless --disable-gpu --run-all-compositor-stages-before-draw --no-pdf-header-footer --print-to-pdf="$PDF_OUTPUT" "$HTML_PREVIEW"
       ```
   - **Regla CSS Exacta Anti-Páginas en Blanco y Anti-Huérfanas:**
     Para evitar que títulos de sección como `## 1. Diagramas de Secuencia` queden solos en una página en blanco antes del primer `###`, combinar obligatoriamente:
     ```css
     h2 { page-break-before: always; }
     h2 + h3 { page-break-before: avoid !important; }
     img { max-height: 70vh !important; page-break-inside: avoid !important; }
     ```
4. **Verificación Visual de Páginas con `pdftoppm` + `view_file`:**
   Convertir las páginas clave del PDF generado a PNG (`pdftoppm -png -r 150 doc.pdf /tmp/page`) e inspeccionarlas con `view_file` antes de responder al usuario.
