---
name: ui-wcag-accessibility-and-browser-qa
description: >-
  Verificación en navegador real (Playwright), Responsive multi-pantalla (262px a 1440px),
  Accesibilidad WCAG 2.2 Nivel AA (useModalA11y, Skip Link, Focus Trap, Escape y alto contraste).
---

# ♿ UI/UX, Accesibilidad WCAG 2.2 AA & Browser E2E Gate

## 1. Estándar de Accesibilidad Digital WCAG 2.2 AA

1. **El Hook Universal `useModalA11y` en TODOS los Modales:**
   - Todo diálogo modal (`ThreatModal`, `ExportModal`, `UserModal`, `DeleteUserModal`, `RolesSection`, `MfaModal`) DEBE implementar `useModalA11y`:
     - Foco automático en el primer elemento interactivo al abrir.
     - Trampa de foco cíclica (`Tab` y `Shift+Tab`) impidiendo que el cursor escape al fondo.
     - Cierre inmediato con la tecla `Escape`.
     - Retorno del foco al botón o elemento desencadenador (`triggerRef`) al cerrarse.
2. **Skip Link Obligatorio (Criterio 2.4.1 AA):**
   - En `MainLayout.jsx`, incluir enlace accesible: `<a href="#main-content" className="sr-only focus:not-sr-only ...">Saltar al contenido principal</a>`.
3. **Contraste y Formularios:**
   - Contraste mínimo **4.5:1** en botones de acción y texto. En botones destructivos (eliminar), asegurar texto legible de alto contraste (`text-slate-950 font-bold` sobre fondos rojos).
   - En inputs de fecha (`type="date"`), forzar `[color-scheme:dark]` en temas oscuros para que el ícono de calendario no se vuelva invisible.
   - Todo campo debe tener `<label htmlFor="...">` conectado o `aria-label`.
4. **Higiene de Sesión en Cliente (Anti-Ghost State):**
   - En `login()`, limpiar `localStorage` y `sessionStorage` para evitar que banderas residuales de cuentas anteriores (como `must_change_password`) bloqueen la navegación de una cuenta legítima.

## 2. Invariantes Matemáticos en Playwright / Navegador
- **Cero Desbordamiento Horizontal:** `document.documentElement.scrollWidth <= window.innerWidth` en viewports canónicos: `262px`, `375px`, `768px`, `1024px` y `1440px`.
- **Cero Colisión de Elementos:** La esfera 3D o animaciones deben tener `shrink-0` y límites elásticos para no truncar logotipos ni títulos.
