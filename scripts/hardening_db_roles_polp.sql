-- =====================================================================================
-- UNIVERSIDAD DE CUNDINAMARCA (UDEC - EXTENSIÓN FACATATIVÁ)
-- PROGRAMA: INGENIERÍA DE SISTEMAS Y COMPUTACIÓN
-- CÁTEDRA: INGENIERÍA DE SOFTWARE II / BASES DE DATOS AVANZADAS
-- DOCENTE EVALUADOR: ING. OSCAR GÓMEZ
-- APLICACIÓN: HoneyMetrics CTI v2.0
-- OBJETIVO: Hardening de Roles de Motor SQL bajo el Principio de Menor Privilegio (PoLP)
-- AUTORES: JOHAN SEBASTIÁN POSADA BELTRÁN & JUAN PABLO FONSECA CELIS
-- FECHA: 2026-11-01
-- MOTOR: POSTGRESQL 16 (PL/pgSQL)
-- TABLA DE MODIFICACIONES:
-- | Versión | Fecha      | Autor                     | Descripción del Cambio                      |
-- | 1.0     | 2026-11-01 | Johan Posada / Juan Fonseca | Creación de rol enjaulado usr_honeymetrics |
-- =====================================================================================
--
-- EXPLICACIÓN EN PRIMERA PERSONA (DEFENSA ACADÉMICA):
-- "Implemento la regla de oro '1 App = 1 Usuario Dedicado' para segregar las responsabilidades
-- de administración del motor respecto a la ejecución en tiempo de ejecución (Runtime DML).
-- El usuario 'usr_honeymetrics' únicamente cuenta con permisos de manipulación de datos (SELECT,
-- INSERT, UPDATE, DELETE) y se le revoca explícitamente el permiso CREATE sobre el esquema public.
-- De esta forma, si la aplicación web sufriera un ataque de inyección SQL, el atacante no podrá
-- alterar la estructura DDL ni crear tablas maliciosas en la base de datos."
-- =====================================================================================

-- 1. Crear el rol / usuario enjaulado de la aplicación si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'usr_honeymetrics') THEN
        CREATE ROLE usr_honeymetrics WITH LOGIN PASSWORD 'hm_secure_password_2026';
    END IF;
END
$$;

-- 2. Conectar a la base de datos y otorgar uso de esquema
GRANT CONNECT ON DATABASE honeymetrics_v2 TO usr_honeymetrics;
GRANT USAGE ON SCHEMA public TO usr_honeymetrics;

-- 3. REVOCAR explícitamente la capacidad de crear tablas, tipos o funciones (DDL)
REVOKE CREATE ON SCHEMA public FROM usr_honeymetrics;

-- 4. OTORGAR permisos estrictamente DML sobre todas las tablas existentes
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO usr_honeymetrics;

-- 5. OTORGAR permisos sobre secuencias para que los autoincrementales funcionen sin error
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO usr_honeymetrics;

-- 6. Garantizar que futuras tablas creadas por migraciones mantengan la misma política PoLP
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO usr_honeymetrics;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO usr_honeymetrics;

-- =====================================================================================
-- SCRIPT DE PRUEBAS Y VERIFICACIÓN EN DBEAVER (RECIBO RDD):
-- =====================================================================================
-- Ejecutar conectado como 'usr_honeymetrics':
--
-- PRUEBA 1 (Debe FALLAR con 'permission denied for schema public'):
-- CREATE TABLE test_should_fail (id int);
--
-- PRUEBA 2 (Debe ser EXITOSA):
-- SELECT id, email, first_names, last_names FROM users LIMIT 1;
-- =====================================================================================
