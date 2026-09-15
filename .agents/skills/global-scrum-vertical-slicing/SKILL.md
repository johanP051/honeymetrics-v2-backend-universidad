---
name: global-scrum-vertical-slicing
description: >-
  Estándar global de Gestión Ágil Scrum, Tajadas Verticales (Vertical Slicing),
  criterios de aceptación BDD (Given-When-Then), Definition of Done (DoD) y desarrollo API-First.
---

# 🏃 Global Scrum & Vertical Slicing Framework

Esta Skill guía la entrega ágil de software para asegurar valor funcional demostrable al final de cada iteración.

## 1. Tajadas Verticales (Vertical Slicing) vs Horizontales
- **PROHIBIDO:** Entregar "solo base de datos" en un sprint y "solo frontend" en el siguiente.
- **OBLIGATORIO:** Cada Historia de Usuario debe entregar una rebanada completa que atraviese todas las capas:
  `UI / Componente React` ➔ `Endpoint API` ➔ `Lógica de Negocio / Service` ➔ `Base de Datos` ➔ `Tests / Documentación`.

## 2. Redacción BDD (Gherkin) para Criterios de Aceptación
Cada funcionalidad debe definirse con el formato:
- **Dado (Given):** El contexto o estado inicial.
- **Cuando (When):** La acción del usuario o evento.
- **Entonces (Then):** El resultado esperado observable.

## 3. Definition of Done (DoD) Universal
Una tarea solo está terminada cuando:
1. El código compila y pasa tests automatizados (Receipt-Driven Development).
2. Cumple con la checklist de seguridad SAST.
3. Los contratos OpenAPI (Swagger) están actualizados.
4. La documentación viva (Obsidian o MkDocs) refleja el cambio.
