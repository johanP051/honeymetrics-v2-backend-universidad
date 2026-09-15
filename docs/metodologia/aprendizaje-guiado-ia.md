# 🎓 Protocolo Pedagógico: Aprendizaje Guiado y Mentoría con IA

> **Navegación:** [← Volver al Índice Central](../README.md) | [← Anterior: Guía Trello & Slack](../guias/puesta-en-marcha-trello-slack.md)

---

## 📑 Tabla de Contenido
1. [Filosofía: La IA como Tech Lead, no como Generador Perezoso](#1-filosofía-la-ia-como-tech-lead-no-como-generador-perezoso)
2. [El Método Socrático en Antigravity](#2-el-método-socrático-en-antigravity)
3. [Cómo Interactuar con el Agente (Prompts Recomendados)](#3-cómo-interactuar-con-el-agente-prompts-recomendados)
4. [El Mecanismo de Escape (Cuando el Tiempo Apremia)](#4-el-mecanismo-de-escape-cuando-el-tiempo-apremia)
5. [Banco de Preguntas Trampa del Docente y Respuestas Senior](#5-banco-de-preguntas-trampa-del-docente-y-respuestas-senior)

---

## 1. Filosofía: La IA como Tech Lead, no como Generador Perezoso

El propósito formativo en la Universidad de Cundinamarca es desarrollar el **criterio arquitectónico, la capacidad de análisis y la argumentación oral** de Johan y Juan Pablo. 

Un desarrollador que solo copia y pega código autogenerado no es capaz de sustentar por qué eligió un código HTTP `422` en lugar de un `400`, o por qué una sesión de base de datos no debe pasarse a la capa de presentación. Por ello, este repositorio integra la skill `aprendizaje-guiado-socratico`.

---

## 2. El Método Socrático en Antigravity

Cuando trabajes con Antigravity en este proyecto, notarás que el agente:
1. **No arroja el archivo completo de golpe.**
2. **Te formula 1 o 2 preguntas reflexivas** sobre el problema:
   - *¿Qué códigos de estado REST aplican?*
   - *¿Qué campos debe ocultar el DTO de salida?*
   - *¿Qué capa debe procesar esta validación?*
3. **Espera tu respuesta para coconstruir la solución.**

Esto garantiza que al momento de escribir el código, tú comprendas cada decisión de ingeniería.

---

## 3. Cómo Interactuar con el Agente (Prompts Recomendados)

### Para Diseñar un Nuevo Endpoint
> *"Antigravity, queremos diseñar el endpoint para el registro de nuevos usuarios. Guíanos paso a paso: ¿qué campos debe recibir el DTO y qué validaciones de seguridad debemos considerar?"*

### Para Comprender un Error Complejo
> *"Antigravity, el test de Pytest me arrojó `422 Unprocessable Entity`. No me des el código corregido de inmediato; explícame qué campo del DTO falló la validación y qué debo inspeccionar."*

---

## 4. El Mecanismo de Escape (Cuando el Tiempo Apremia)

Si estás a pocas horas de la entrega del martes y requieres desbloquearte rápidamente, puedes utilizar el **comando de escape explícito**:

> *"Antigravity, no me des más pistas, arroja la solución técnica completa y explícame brevemente el porqué de cada bloque."*

El agente desactivará el interrogatorio socrático temporalmente y entregará el código probado con RDD.

---

## 5. Banco de Preguntas Trampa del Docente y Respuestas Senior

Prepárate para la sustentación del martes con estas 5 preguntas clásicas de jurados y profesores:

### Pregunta 1: *"¿Por qué crearon una capa de servicios (`services/`) si podían meter la consulta de base de datos directamente en el endpoint?"*
> **Respuesta Senior:**  
> *"Profesor, aplicar el patrón Service Layer garantiza el principio de Responsabilidad Única (SRP) de SOLID y Thin Controllers. Si ponemos la lógica en el endpoint, acoplamos las reglas de negocio al protocolo HTTP. Al encapsular la lógica en el servicio, podemos reutilizarla desde tareas en segundo plano (Celery/Cron), scripts CLI o invocarla en pruebas unitarias con Pytest en milisegundos sin levantar clientes HTTP."*

### Pregunta 2: *"¿Por qué usan DTOs con Pydantic en lugar de recibir directamente diccionarios JSON en Python?"*
> **Respuesta Senior:**  
> *"Porque los diccionarios carecen de tipado estricto en tiempo de ejecución. Pydantic v2 realiza validación estructural de tipos, coerción de datos, documentación automática en OpenAPI/Swagger y, lo más importante: actúa como un cortafuegos para evitar la Fuga de Entidades (Entity Leakage), impidiendo que hashes de contraseñas o campos internos de la base de datos se expongan accidentalmente al cliente."*

### Pregunta 3: *"¿Por qué separaron el proyecto en 3 repositorios en lugar de un monolito?"*
> **Respuesta Senior:**  
> *"Para cumplir con el estándar de Arquitectura Desacoplada y el principio API-First. Esto permite que el ciclo de vida del frontend (React SPA) sea independiente del backend (FastAPI), facilitando despliegues autónomos, evitando acoplamientos en el historial de Git y permitiendo que el Frontend utilice Mocks offline en caso de contingencia de red."*

### Pregunta 4: *"¿Cómo mitigan vulnerabilidades de inyección SQL?"*
> **Respuesta Senior:**  
> *"A través de dos mecanismos: primero, el uso del ORM declarativo de SQLAlchemy con consultas parametrizadas obligatorias; segundo, la validación y sanitización previa de cada entrada en la capa DTO antes de que los datos alcancen la persistencia."*

### Pregunta 5: *"¿Por qué tienen tres archivos de docker-compose?"*
> **Respuesta Senior:**  
> *"Implementamos el patrón Compose Override: `docker-compose.yml` define los servicios base; `docker-compose.override.yml` se aplica automáticamente en desarrollo para habilitar Live-Reload y exponer puertos al host; y `docker-compose.prod.yml` aplica hardening para producción, eliminando los puertos de base de datos expuestos al host y ejecutando bajo un usuario sin privilegios (`appuser`)."*

---

> **Navegación:** [← Volver al Índice Central](../README.md) | [← Anterior: Guía Trello & Slack](../guias/puesta-en-marcha-trello-slack.md)
