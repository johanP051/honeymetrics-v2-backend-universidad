---
name: rbac-and-db-engine-governance
description: >-
  Gobernanza de Control de Acceso en 2 Niveles (Matriz RBAC de Negocio + Roles de Motor SQL PoLP)
  y Estándar Docente para Stored Procedures (SPs) y Triggers en PostgreSQL 16 / DBeaver.
---

# 🔐 RBAC de Negocio, Seguridad de Motor SQL y Estándar de SPs/Triggers

## 1. Separación Estricta de Roles en 2 Niveles (Defensa en Profundidad)

### Nivel 1: Roles del Motor de Base de Datos (PostgreSQL PoLP)
- **MUST NOT:** Prohibido conectar la API en producción como superusuario `postgres`.
- **MUST (Script de Hardening PoLP — `scripts/hardening_db_roles_polp.sql`):**
  - Implementar la regla *"1 App = 1 Usuario Dedicado"* creando el usuario enjaulado `usr_<app>` (ej. `usr_honeymetrics`) con permisos estrictamente DML y ejecutando:
    ```sql
    REVOKE CREATE ON SCHEMA public FROM usr_<app>;
    ```
  - **Recibo RDD Obligatorio:** Verificar que `CREATE TABLE test_should_fail (id int);` falle con `ERROR: permission denied for schema public`.
  - **Protocolo de Migración Alembic en Producción:** Las migraciones DDL (`alembic upgrade head`) se ejecutan como dueño del esquema (`postgres` o `<app>_migrator`). Tras crear una nueva tabla (ej. `mfa_backup_codes`), se debe otorgar inmediatamente permiso DML al usuario enjaulado:
    ```sql
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE <nueva_tabla> TO usr_<app>;
    ```

### Nivel 2: Roles de Negocio y Matriz Dual (A: PoLP vs B: PBAC)
- **MUST:** Documentar siempre en el Manual Técnico y Diccionario de Datos:
  1. **Matriz A (Privilegios de Motor SQL):** `postgres` (DBA SSH) vs `usr_<app>` (App Runtime DML) vs `<app>_migrator` (DDL).
  2. **Matriz B (Control de Acceso PBAC):** Roles de negocio cruzados contra los scopes granulares del JWT.
- **MUST (Equivalencia Canónica de Roles):** En `app/core/permissions.py`, soportar tanto `"Superusuario"` como `"Administrador"` con el bloque completo de scopes, y soportar variaciones con tilde o apellido (`"Directivo de T.I."`, `"Analista de datos"`, `"Consultor de Ciberseguridad"`).
- **MUST (Separación de Funciones):** Scopes separados para consultar (`:read`), editar (`:write`), eliminar (`:delete`) y aprobar (`:approve`).

## 2. Estándar Académico para Stored Procedures (SPs) y Triggers en PostgreSQL 16
Todo SP y Trigger entregado para evaluación académica debe incluir:
1. **Encabezado Formal Docente:** Con `APLICACION`, `OBJETIVO`, `AUTOR`, `FECHA` y tabla de modificaciones.
2. **Comentarios en Primera Persona:** Explicando la lógica transaccional (`-- Declaro...`, `-- Inicio la transacción...`).
3. **Script de Pruebas para DBeaver:** Bloque SQL listo para ejecutar y capturar evidencia.
