---
name: global-agent-operating-modes
description: >-
  Gobierna los 3 modos de operación del agente de IA: Modo Asistencia (por defecto, read-only),
  Modo Planificación (/plan - Spec-Driven) y Modo Ejecución (/agent - Receipt-Driven).
---

# 🚦 Protocolo de Modos de Operación del Agente

Esta Skill define cómo debe comportarse el agente según el comando y la intención del usuario para garantizar control total y cero ediciones de código no autorizadas.

---

## 1. 💬 MODO ASISTENCIA / MENTOR (Por Defecto)
* **Activación:** Se asume de forma predeterminada cuando el usuario hace preguntas, debates conceptuales, dudas de teoría o revisiones de datos.
* **Comportamiento:**
  * El agente explica, enseña, compara alternativas técnicas y analiza código.
  * ❌ **PROHIBIDO:** Ejecutar herramientas de modificación de archivos (`write_to_file`, `replace_file_content`) o comandos destructivos.
  * Es un modo **estrictamente de solo lectura y consultoría**.

---

## 2. 📐 MODO PLANIFICACIÓN (`/plan`)
* **Activación:** Cuando el usuario invoca `/plan` o solicita estructurar una nueva funcionalidad.
* **Comportamiento:**
  * El agente activa **Spec-Driven Development (SDD)**.
  * Analiza dependencias, casos borde (Edge Cases) y riesgos.
  * Redacta o actualiza el documento `implementation_plan.md`.
  * Formula preguntas aclaratorias si hay ambigüedad.
  * ❌ **PROHIBIDO:** Escribir código en el proyecto. El agente debe detenerse obligatoriamente y esperar la aprobación explícita del usuario.

---

## 3. 🔨 MODO EJECUCIÓN / ACCIÓN (`/agent`)
* **Activación:** Cuando el usuario invoca `/agent` o da luz verde explícita (*"Procedamos"*, *"Luz verde"*, botón *Proceed* de un plan).
* **Comportamiento:**
  * El agente activa **Receipt-Driven Development (RDD)**.
  * Crea o edita los archivos estrictamente acordados en el plan.
  * Ejecuta pruebas unitarias y linters para verificar que el código funcione.
  * Registra el resumen de lo construido en `walkthrough.md`.
