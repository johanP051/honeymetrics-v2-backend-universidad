---
name: pr-code-reviewer
description: >-
  Auditoría estricta de Pull Requests, Clean Architecture N-Capas,
  Receipt-Driven Development y políticas de ramas Git antes de integrar a develop o main.
---

# 🏛️ Clean Architecture & PR Quality Gate

## Criterios de Bloqueo Inmediato (Request Changes)
1. **Backend:**
   - 0 consultas ORM directas (`db.query`) en routers de `app/api/`.
   - 0 endpoints sin `response_model` tipado.
   - 0 llamadas mutantes (`POST`, `PUT`, `DELETE`) en endpoints `GET` (CQS).
   - 0 `Base.metadata.create_all()` en tiempo de importación.
2. **Frontend:**
   - 0 llamadas directas a `api/` desde componentes visuales o utilidades (todo en Custom Hooks).
   - 0 archivos que superen las **200 líneas**.
   - 0 mocks activos en compilaciones de producción (`import.meta.env.PROD`).
   - Cero banderas residuales en `localStorage` tras login.
3. **Gobernanza Git:**
   - Prohibido hacer PRs directos a `main` que no provengan de `develop` (`branch-policy.yml`).
   - Prohibido `git add .` sin revisión de `git status --short` y `git diff`.
   - `docs/entregables_profesor/` y `.env.*` deben estar estrictamente ignorados en `.gitignore`.
