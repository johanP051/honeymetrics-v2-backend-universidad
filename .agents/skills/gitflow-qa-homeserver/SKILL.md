---
name: gitflow-qa-homeserver
description: Protocolo estricto de GitFlow y Despliegue de QA en el Home Server para HoneyMetrics v2. Prohíbe terminantemente realizar commits directos en ramas protegidas (QA y main). Obliga el uso de ramas de trabajo (feat/, fix/, hotfix/), integración previa en develop, promoción controlada a QA, back-merge obligatorio de parches y validación con pruebas E2E en el Home Server (192.168.31.235) con recreación de contenedores y recarga de variables .env.
---

# 🌿 Skill: GitFlow Estricto y Ciclo de Vida QA en Home Server

## 🎯 Propósito
Garantizar la disciplina arquitectónica y la trazabilidad de código en HoneyMetrics v2 Universidad, eliminando de raíz el antipatrón de commitear parches directamente en la rama QA o desincronizar la rama develop respecto al trabajo de los compañeros de equipo (frontend y backend).

---

## 🚫 Reglas de Oro Inquebrantables

### 1. Cero Commits Directos en QA y main
- **PROHIBIDO:** Queda terminantemente vetado hacer `git commit` directamente estando parado en la rama `QA` o `main`.
- Todo cambio, por pequeño que sea (incluso una coma, una variable o una migración de base de datos), **DEBE** nacer en una rama de trabajo semántica:
  - `feat/<nombre-funcionalidad>` para nuevas características.
  - `fix/<nombre-error>` para corrección de bugs en desarrollo.
  - `hotfix/<nombre-incidente>` para emergencias críticas.

### 2. Cadena de Integración Ascendente (El Orden Sagrado)
El flujo de avance de código es unidireccional y ascendente:
```text
rama de trabajo (feat/ / fix/)
         ⬇ (Pruebas unitarias pytest locales pasando al 100%)
      develop (Integración troncal de equipo)
         ⬇ (Promoción controlada de Sprint)
        QA (Estabilización y Despliegue en Home Server)
         ⬇ (Aprobación docente / release final con PR sin auto-aceptar)
       main (Producción)
```

### 3. Back-Merge Obligatorio de Estabilización
Si durante la fase de auditoría en QA se detecta un bug y se aplica un parche:
1. El parche se desarrolla en una rama `fix/`.
2. Se mezcla primero en `develop`.
3. Se promueve de `develop` a `QA`.
4. Si por alguna excepción extrema se aplica un parche que toca `QA`, es **obligatorio e inmediato** ejecutar el back-merge: `git checkout develop && git merge QA && git push origin develop`.

---

## 🏗️ Protocolo de Despliegue y Pruebas en el Home Server (192.168.31.235)

Una vez que el código esté promovido legalmente en la rama `QA`, el agente debe seguir este checklist de despliegue antes de declarar cualquier prueba como válida:

### Paso 1: Actualización del Repositorio en el Servidor
```bash
ssh -p 22 jsebas@192.168.31.235 'cd /home/jsebas/honeymetrics-v2-backend-universidad && git pull origin QA'
```

### Paso 2: Recreación Obligatoria de Contenedores (`--force-recreate`)
> `docker restart` NO recarga cambios en el archivo `.env`. Si se modifican variables (ej. `RESEND_API_KEY`, `FRONTEND_URL`), el contenedor DEBE ser recreado:
```bash
ssh -p 22 jsebas@192.168.31.235 'cd /home/jsebas/honeymetrics-v2-backend-universidad && docker compose up -d --no-deps --force-recreate api'
```

### Paso 3: Aplicación de Migraciones de Base de Datos
Si la actualización incluyó cambios de modelos o esquemas:
```bash
ssh -p 22 jsebas@192.168.31.235 'docker exec hm_v2_api alembic upgrade head'
```

### Paso 4: Verificación de Observabilidad y Recibos (RDD)
Antes de invitar al usuario a probar o certificar el endpoint:
1. Inspeccionar logs limpios: `docker logs --tail 30 hm_v2_api`.
2. Verificar túnel Cloudflare enrutado: `curl -I https://api-honey-v2-homeserver.johan-d3v.site/docs`.
3. Confirmar que las variables de entorno están vivas dentro del contenedor: `docker exec hm_v2_api env | grep <VARIABLE>`.
