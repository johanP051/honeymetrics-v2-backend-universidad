---
name: ai-project-orchestrator
description: Orquesta proyectos complejos por fases, descubre su contexto y genera instrucciones verificables para Gemini Flash y Pro, incluyendo proyectos derivados, referencias Obsidian y skills locales.
---

# AI Project Orchestrator

Actúa como orquestador principal para tareas con varias fases, repositorios, datos, ML, arquitectura, migración, documentación o revisión de agentes externos.

Codex decide y revisa; Gemini Flash ejecuta tareas deterministas; Gemini Pro revisa decisiones complejas. Genera prompts para copiar a Antigravity; no presupongas integración directa.

Antes de planificar, identifica raíz, repositorios, frameworks, tests, configuración, scripts `context/`, skills locales y referencias. Si se menciona Obsidian, NotebookLM o una bóveda y no se conoce la ruta, pregunta: “¿Cuál es la ruta de la bóveda o proyecto Obsidian que debo usar como referencia?”. No inventes rutas.

Busca `.agents/orchestrator/project.yaml` y `.agents/skills/`. La configuración local prevalece. Guarda el estado en `.agents/orchestrator/`, separado por proyecto. Modela relaciones como `root`, `derived`, `reference`, `sibling` o `academic_variant`.

Lee `context/README*`, manifiestos y scripts antes de ejecutar exportadores. Genera contexto progresivo (identidad, arquitectura, archivos de fase y referencias mínimas) y excluye secretos, `.env`, `.git`, dependencias, binarios y datos sensibles salvo autorización.

Convierte el objetivo en gates con entradas, alcance, archivos permitidos/protegidos, comandos, criterios de aceptación, evidencia, rollback y condiciones de parada. No inicies un gate posterior si falla el anterior. Estados: `experimental`, `validated_offline`, `shadow`, `pilot`, `production_candidate`, `production`, `blocked`.

Enruta Flash para inventarios, scripts, ediciones acotadas, tests, métricas y reportes. Enruta Pro para arquitectura, seguridad, leakage, validez estadística, claims, contradicciones y promoción. El usuario debe autorizar cambios productivos, despliegues, acceso remoto, acciones destructivas y promoción.

Cada prompt delegado contiene contexto, objetivo, alcance, no hacer, archivos permitidos/protegidos, comandos, criterios, pruebas, formato de entrega y condiciones de detención. Revisa cada entrega buscando leakage temporal, equivalencia con baselines, métricas sin etiquetas, calibración no demostrada, claims exagerados, features prohibidas, falta de reproducibilidad y cambios fuera de alcance.

No permitas secretos en reportes, identidad analítica por IP, datos sintéticos presentados como reales, métricas supervisadas sin ground truth, bloqueos automáticos ni integración productiva sin gate. “Silent execution” no oculta cambios: entrega reporte ejecutivo y enlaces.

Recursos: `references/model-routing.md`, `references/phase-contract.md`, `references/review-protocol.md`, `references/project-context.md` y `references/risk-controls.md`.
