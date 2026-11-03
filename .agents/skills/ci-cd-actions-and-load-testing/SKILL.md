---
name: ci-cd-actions-and-load-testing
description: >-
  Estándar de CI/CD (GitHub Actions con justificación técnica y cobertura >= 70%)
  y Pruebas No Funcionales de Rendimiento (Load, Stress, Spike Testing, SLAs p50/p95/p99 y K8s).
---

# ⚡ CI/CD GitHub Actions & Performance / Load Testing Standard

## 1. Estándar de Ingeniería para GitHub Actions (`.github/workflows/`)
1. **Tabla de Justificación Técnica:** Todo step en el workflow debe justificar qué hace, por qué se eligió y qué riesgo previene.
2. **Quality Gates Obligatorios:**
   - Permisos mínimos: `permissions: contents: read`.
   - Control de concurrencia: `concurrency: cancel-in-progress: true`.
   - Linting y formateo: `ruff check . && black --check .`.
   - SAST y dependencias: `bandit -r app/ -ll -ii` y `pip-audit`.
   - **Quality Gate de Cobertura $\ge 70\%$:** `pytest --cov=app --cov-fail-under=70`.
   - Docker Smoke Test: `docker build -t app:smoke -f Dockerfile .`.

## 2. Pruebas de Rendimiento y SLAs
1. **Load Testing (Carga normal):** 50–100 usuarios concurrentes midiendo RPS y percentiles ($p95 < 100\text{ ms}$ en CRUD, $p95 < 50\text{ ms}$ en ML).
2. **Stress Testing (Punto de ruptura):** Incrementar carga hasta saturación comprobando que el servidor responda `429`/`503` sin corromper la BD y se recupere solo al cesar el tráfico.
3. **Dimensionamiento del Pool de SQLAlchemy:**
   $$\text{Replicas} \times \text{Workers} \times (\text{pool\_size} + \text{max\_overflow}) < \text{max\_connections de Postgres}$$
