---
name: session-handoff-and-context-continuity
description: >-
  Protocolo de compactación de memoria, persistencia en Engram/project_state.json y
  generación automatizada de prompts de transferencia (Handoff Snapshots <= 1500 tokens).
---

# 🔁 Session Handoff, Memory Compaction & Context Continuity Standard

## 1. Principio de Cero Fricción y Prevención de Context Rot
Cuando un chat supere los 300k tokens o se agote la cuota de un agente, se genera un **Handoff Snapshot** de menos de 1.500 tokens en `.agents/orchestrator/prompt_reanudacion.md` para abrir una sesión fresca en segundos.

## 2. Los 5 Bloques del Snapshot
1. **Estado de Git Real:** Rama activa, último commit y `git status --short`.
2. **Quality Gates y Pruebas Verificadas:** Conteo real de tests pasando (ej. 351 tests en verde).
3. **Decisiones Técnicas Cerradas (ADRs en Caliente):** Decisiones ya acordadas que la nueva sesión no debe reabrir.
4. **Próximos 3 Pasos Inmediatos:** Rutas exactas de archivos y acciones concretas.
5. **Instrucción Inmediata:** Directiva para arrancar sin resúmenes innecesarios.

## 3. Gobernanza de Engram (Memorias Canónicas)
- **Prohibido acumular memorias sueltas:** Mantener y actualizar **una única memoria maestra canónica por proyecto** en Engram (ej. `#442` para infraestructura de HoneyMetrics), consolidando o sobreescribiendo notas viejas.
- **Documentación al Lado del Código:** Mantener puertos y túneles en `INFRASTRUCTURE.md` y `.env.example` para no depender de wikis externas.
