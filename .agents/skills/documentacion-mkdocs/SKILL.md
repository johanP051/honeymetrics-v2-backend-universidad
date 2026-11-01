---
name: documentacion-mkdocs
description: >-
  Documentación en 3 Etapas: (1) MkDocs modular en docs/, (2) Pre-entregables Markdown UDEC en
  docs/entregables_profesor/ (en .gitignore), y (3) Compilación fiel a Word (.docx) para Oscar Gómez.
---

# 📚 Skill: Documentación Viva en MkDocs & Entregables Académicos en DOCX

## 1. La Separación Estricta de los 2 Mundos Documentales
1. **Mundo Repositorio (`docs/` — Etapa 1):**
   - Documentación modular de ingeniería para desarrolladores y MkDocs.
   - **PROHIBIDO** incluir portadas de la universidad, nombres de asignaturas o tablas de `Aprobado: Oscar Gómez` en los archivos de `docs/`.
   - Cada archivo inicia con `> **Ver también:**` e `## Índice`.
2. **Mundo Universidad (`docs/entregables_profesor/` — Etapas 2 y 3):**
   - Documentos monolíticos 100% autocontenidos para el profesor Oscar Gómez.
   - **MUST:** La carpeta `docs/entregables_profesor/` y `site/` **SIEMPRE DEBEN ESTAR EN `.gitignore`**.
   - Incluyen Portada UDEC, tablas `REGISTRO DE CAMBIOS` y `CONTROL DEL DOCUMENTO (Aprobado: Oscar Gómez)`, incrustando todas las tablas, diagramas y guías en línea (prohibido delegar con enlaces relativos `../`).
   - Lenguaje 100% de usuario final en el Manual de Usuario (cero nombres de variables de código como `ROLES_TO_SCOPES`).

## 2. Protocolo "Director de Cine" en Playwright (Videos 1080p + Capturas Reales)
1. **Resolución 1080p Nativa:** Grabar siempre con `viewport={"width": 1920, "height": 1080}`, `record_video_size={"width": 1920, "height": 1080}` y transcodificar con `ffmpeg -crf 18`.
2. **Puntero Dorado Inyectado:** Cursor `#hm-cursor` de 24px en `document.documentElement` con movimiento progresivo (`steps=28`) y destello en clics.
3. **Flujos Completos:** Prohibido abrir modales para cerrarlos vacíos; cada video debe mostrar la transacción guardada y reflejada en la tabla.
4. **Censura de Secretos:** Aplicar `filter: blur(7px)` sobre códigos QR y semillas TOTP antes de capturar pantallas de MFA.

## 3. Renderizado Limpio en MkDocs Material
1. **Prohibido alertas de GitHub:** Convertir `> [!NOTE]` a `!!! note "⚡ Nota"` con sangría de 4 espacios.
2. **Doble salto de línea:** Insertar siempre `

` entre un párrafo terminado en dos puntos (`:`) y el primer elemento de una lista (`1. ` o `- `) para que no se colapsen.
3. **Atributo `poster` obligatorio:** Toda etiqueta `<video>` debe incluir `poster="assets/screenshots/...png"`.
