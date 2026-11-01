---
name: honeymetrics-project-bootstrap
description: Inicializa o audita reglas portables de Git, commits, PRs, CI y despliegue para proyectos nuevos o existentes, con compatibilidad para Codex, OpenCode, Antigravity y Claude Code.
---

# HoneyMetrics Project Bootstrap

Cuando se cree o estandarice un proyecto, genera o actualiza `AGENTS.md`, `CLAUDE.md` y `.agents/rules/` sin sobrescribir instrucciones existentes. Mantén separadas las reglas del stack y la política Git.

Selecciona el perfil según las ramas reales del repositorio. Guía: rama auxiliar (`feat/*`, `fix/*`, `security/*`, `test/*`, `docs/*` o `chore/*`) → PR a `develop` → validación → PR a `main`. Académico/staging: rama auxiliar → PR a `develop` → PR a `QA` → pruebas QA → PR a `main`. No se permite push directo; `main` requiere aprobación humana. No inventes ni crees `QA` automáticamente.

Usa Conventional Commits y commits atómicos. No uses `git add .` ni `git commit -a`. Clasifica checks como obligatorios, condicionales e informativos; no bloquees con checks inestables sin evidencia.

Antes de push, merge, auto-merge, protección remota, despliegue o eliminación de datos, muestra el plan y solicita confirmación. Nunca uses `docker compose down -v` automáticamente. Entrega evidencia, riesgos, rollback y pendientes.
