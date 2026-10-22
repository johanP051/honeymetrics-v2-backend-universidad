# Workflow Git y releases — perfil académico

- Ramas auxiliares: `feat/*`, `fix/*`, `security/*`, `test/*`, `docs/*`.
- `develop`: integración.
- `QA`: staging y validación en el servidor QA.
- `main`: versión estable y aprobación humana.

Flujo obligatorio: rama auxiliar → PR `develop` → PR `QA` → pruebas QA → PR `main`. No se permite push directo a `develop`, `QA` o `main`.

Usar Conventional Commits y commits atómicos. No usar `git add .` ni `git commit -a`. Push, merge, auto-merge, protecciones remotas, despliegues y destrucción de datos requieren confirmación explícita.
