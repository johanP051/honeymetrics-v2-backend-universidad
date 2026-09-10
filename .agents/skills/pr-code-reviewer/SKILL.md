---
name: pr-code-reviewer
description: >-
  Skill de Auditoría y Revisión de Pull Requests para HoneyMetrics. Evalúa código de FastAPI y React,
  enforza Clean Architecture, componentes atómicos, Mocks offline, Conventional Commits y mitigación SAST.
---

# 🔍 Pull Request Code Reviewer & Quality Guardian

Esta Skill gobierna la revisión técnica de Pull Requests (PRs) para garantizar que todo código que entre a las ramas `develop` o `main` cumpla con los más altos estándares de calidad, seguridad y arquitectura.

---

## 📋 Checklist de Auditoría por Capa

### 1. ⚛️ Frontend (React + SWC)
- [ ] **Componentes Atómicos:** Los archivos `.jsx` en `src/components/` deben ser modulares y no exceder **200 líneas**. Si contienen múltiples responsabilidades, deben dividirse en subcomponentes.
- [ ] **Thin Components & Custom Hooks:** Prohibido hacer llamadas directas `fetch()` o `axios` dentro del JSX. La lógica de peticiones y estado debe vivir en `src/hooks/` (ej. `useThreats.js`).
- [ ] **Mocks Offline Intactos:** Si se agrega un nuevo endpoint o vista, debe incluirse su dataset simulado en `src/mocks/` con fallback en caso de desconexión.
- [ ] **Cero Estilos Hardcodeados:** Usar las variables CSS globales de `src/index.css` (`var(--bg-primary)`, `var(--accent-amber)`, etc.).
- [ ] **Compilación Limpia:** `npm run build` debe ejecutar sin errores de compilación ni advertencias de variables no usadas.

---

### 2. ⚡ Backend (FastAPI + Clean Architecture)
- [ ] **Thin Routers (<15 líneas):** Los endpoints en `app/api/v1/endpoints/` solo reciben la petición, delegan en `app/services/` y retornan el modelo. Cero lógica de negocio en el router.
- [ ] **DTOs con Pydantic v2:** Todo endpoint debe tener definido su `response_model` y validar entradas estrictamente.
- [ ] **Testing Obligatorio con Pytest:** Cada nuevo endpoint debe incluir sus pruebas unitarias en `tests/api/v1/test_<modulo>.py`. `pytest` debe pasar al 100%.
- [ ] **12-Factor App:** Cero credenciales, URLs o IPs quemadas en código fuente.

---

### 3. 🛡️ Seguridad SAST (AppSec)
- [ ] **Prevención de Inyección:** Cero queries SQL concatenadas o comandos de shell dinámicos.
- [ ] **CORS y Autenticación:** Endpoints protegidos con dependencias de seguridad y verificación de tokens.
- [ ] **Manejo de Errores:** Prohibido el uso de `except Exception: pass` silencioso. Usar excepciones HTTP explícitas (`HTTPException(status_code=400, detail=...)`).

---

### 4. 🌿 Git & Conventional Commits
- [ ] **Mensajes de Commit:** Deben seguir el formato `tipo(alcance): descripción` (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- [ ] **Sin Archivos Basura:** No deben incluirse `.env`, `node_modules/`, `venv/`, `__pycache__/` ni archivos temporales del IDE.

---

## 📊 Formato del Reporte de Revisión de PR

Al auditar una PR o rama, el agente generará el veredicto en este formato:

```markdown
### 📋 Reporte de Auditoría de PR: [Nombre de la Rama]

**Estado:** [ ✅ APROBADA PARA MERGE | ⚠️ REQUIERE AJUSTES ]

#### 🟢 Puntos Fuertes:
- Cumple con ...

#### ⚠️ Observaciones y Ajustes Solicitados:
1. **Archivo / Línea:** `src/components/Ejemplo.jsx:45`
   - **Problema:** ...
   - **Solución Recomendada:** ...

#### 💬 Feedback listo para copiar y pegar para el autor:
> [Mensaje constructivo y amigable para el compañero]
```
