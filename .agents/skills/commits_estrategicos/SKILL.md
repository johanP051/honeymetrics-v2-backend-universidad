---
name: commits-estrategicos
description: >-
  Estándar de Versionamiento Estratégico (Micro-Commits lógicos post-desarrollo) para el proyecto HoneyMetrics. Prohíbe el uso de `git add .` masivos y obliga al agente a desglosar el trabajo terminado en commits atómicos, consultando siempre la autoría dinámica (Co-authored, Override).
---

# 🌳 Commits Estratégicos y Autoría (Anti-IA Suspicion)

Esta Skill define cómo el agente debe comportarse al momento de guardar el código en Git dentro de los repositorios de HoneyMetrics, asegurando un historial limpio, auditable y que refleje un trabajo humano metódico.

## 1. La Regla de Oro del Versionamiento
El agente tiene total libertad para programar grandes bloques de código y probar funcionalidades completas de una sola vez. **Sin embargo**, al momento de subir los cambios, **ESTÁ ESTRICTAMENTE PROHIBIDO usar `git add .` o `git commit -a`**.

## 2. El Protocolo de Commits Fraccionados
Una vez que una funcionalidad (ej. un Endpoint, un CRUD) está probada y lista, el agente debe guiar al usuario para empaquetar los archivos en **bloques lógicos (Commits Atómicos)**.

El proceso debe ser el siguiente:
1. **Analizar los cambios:** El agente revisa qué archivos fueron creados o modificados.
2. **Proponer el Fraccionamiento:** El agente agrupa los archivos por su propósito (ej. Modelos de BD, Lógica de Negocio, Frontend UI, Documentación).
3. **Preguntar Autoría (Dinámica):** Por CADA bloque lógico, el agente DEBE preguntarle al usuario: *"¿A nombre de quién debe quedar este commit? ¿Tuyo, de tu compañero, o Co-Authored?"*

### Ejemplo del Flujo Correcto:
> **Agente:** "El desarrollo del Login está completo. Vamos a subirlo en 3 commits atómicos. Para el primer commit (Base de Datos), ¿quién es el autor?"
> 
> **Usuario:** "Ponlo a nombre de Juan Pablo."
> 
> **Agente:** "Perfecto. Ejecuta esto:
> `git add app/models/user.py app/schemas/user.py`
> `git commit --author="Juan Pablo Fonseca <correo@gmail.com>" -m "feat(db): crear modelos de usuario"`
> 
> Ahora, para el segundo commit (Lógica JWT), ¿quién es el autor?"

## 3. Formato de Mensajes (Conventional Commits)
Todos los commits deben seguir el estándar *Conventional Commits*:
- `feat:` (nuevas funcionalidades)
- `fix:` (solución de bugs)
- `docs:` (cambios en documentación / UML)
- `refactor:` (mejoras de código sin cambiar funcionalidad)
- `chore:` (tareas de mantenimiento, dependencias)

*Nota: Para aplicar overrides de autor, consultar la nota conceptual del usuario sobre `--author` y `Co-authored-by`.*
