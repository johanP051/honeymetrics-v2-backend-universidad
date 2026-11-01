# HoneyMetrics Académico Backend

Consulta `.agents/rules/` antes de cambios Git, CI o despliegues. Este repositorio usa el perfil académico: rama auxiliar → `develop` → `QA` → `main`. Conserva las reglas de arquitectura, Scrum, seguridad y ML existentes.

## 🚨 REGLA CERO: SECURE-BY-DESIGN, ENTREVISTA DE PLANIFICACIÓN Y AUTO-AUDITORÍA
En solicitudes de creación de aplicación, sprint, historia, endpoint, vista o refactorización:
1. Antes de implementar, aplicar Fail-Closed y presentar las preguntas arquitectónicas pertinentes de `global-agent-operating-modes` (RBAC, accesibilidad, base de datos, CI/CD, despliegue y entregables académicos).
2. Antes de cerrar, aplicar `global-security-sast`, el quality gate `pr-code-reviewer`, QA accesible cuando corresponda y mantener `docs/` actualizado. Revisar el diff con la auto-auditoría adversarial de seis puntos y reportar evidencia real.
## Skills obligatorias de arquitectura y continuidad
- Aplicar `clean-architecture-and-code-hygiene` durante la planificación y escritura/modificación de código.
- Aplicar `session-handoff-and-context-continuity` al preparar relevos o snapshots de reanudación de sesión.
