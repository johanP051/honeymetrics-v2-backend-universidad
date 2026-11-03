-- =====================================================================================
-- UNIVERSIDAD DE CUNDINAMARCA (UDEC - EXTENSIÓN FACATATIVÁ)
-- PROGRAMA: INGENIERÍA DE SISTEMAS Y COMPUTACIÓN
-- CÁTEDRA: INGENIERÍA DE SOFTWARE II / BASES DE DATOS AVANZADAS
-- DOCENTE EVALUADOR: ING. OSCAR GÓMEZ
-- APLICACIÓN: HoneyMetrics CTI v2.0
-- OBJETIVO: Catálogo Oficial de Programabilidad en Base de Datos (5 SPs + 5 Triggers)
-- AUTORES: JOHAN SEBASTIÁN POSADA BELTRÁN & JUAN PABLO FONSECA CELIS
-- FECHA: 2026-11-03
-- MOTOR: POSTGRESQL 16 (PL/pgSQL)
-- TABLA DE MODIFICACIONES:
-- | Versión | Fecha      | Autor                     | Descripción del Cambio                                      |
-- | 1.0     | 2026-11-01 | Johan Posada / Juan Fonseca | Entrega inicial de 3 Triggers y 3 SPs auditables           |
-- | 2.0     | 2026-11-03 | Johan Posada / Juan Fonseca | Catálogo completo: 5 Triggers y 5 SPs con salvaguardas SOC |
-- =====================================================================================

-- =====================================================================================
-- 1. TRIGGER 1: BÓVEDA FORENSE INMUTABLE Y AUDITORÍA AL ELIMINAR IPs DE LA LISTA NEGRA
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Módulo de Gestión de Amenazas (Threat Intelligence Center)
-- OBJETIVO: Capturar automáticamente las filas eliminadas en blacklist_entries para archivarlas
--           en la tabla inmutable blacklist_audit_vault y generar la traza en audit_logs.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Diseño este trigger AFTER DELETE sobre la tabla blacklist_entries para garantizar el principio
-- forense de No Repudio. Cada vez que un analista o administrador da de baja una IP sospechosa,
-- capturo el registro histórico que se pretendía destruir, lo serializo como snapshot JSON, lo inserto
-- en blacklist_audit_vault y finalmente registro la evidencia en audit_logs."
-- =====================================================================================

CREATE OR REPLACE FUNCTION fn_trg_audit_blacklist_deletion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro la variable donde ensamblaré el snapshot serializado en formato JSON
    v_snapshot JSON;
BEGIN
    -- Construyo el objeto JSON con la totalidad de los valores del registro eliminado (OLD)
    v_snapshot := json_build_object(
        'original_id', OLD.id,
        'ip', OLD.ip,
        'ip_type', OLD.ip_type,
        'country', OLD.country,
        'threat_score', OLD.threat_score,
        'category', OLD.category,
        'status', OLD.status,
        'notes', OLD.notes,
        'blocked_by_user_id', OLD.blocked_by_user_id,
        'created_at', OLD.created_at
    );

    -- Inserto la copia inmutable en la tabla de bóveda forense blacklist_audit_vault
    INSERT INTO blacklist_audit_vault (
        original_entry_id,
        original_ip,
        ip_type,
        country,
        threat_score,
        category,
        status,
        notes,
        deleted_by_user_id,
        full_record_json,
        created_at,
        deleted_at
    ) VALUES (
        OLD.id,
        OLD.ip,
        OLD.ip_type,
        OLD.country,
        OLD.threat_score,
        OLD.category,
        OLD.status,
        OLD.notes,
        OLD.blocked_by_user_id,
        v_snapshot,
        OLD.created_at,
        NOW() AT TIME ZONE 'UTC'
    );

    -- Inserto el evento de auditoría en la tabla general de trazabilidad audit_logs
    INSERT INTO audit_logs (
        actor_user_id,
        actor_email,
        action,
        entity_name,
        entity_id,
        details,
        ip_address,
        created_at
    ) VALUES (
        OLD.blocked_by_user_id,
        'TRIGGER_DB_ENGINE',
        'BLACKLIST_IP_ARCHIVED_TO_VAULT',
        'blacklist_entries',
        OLD.id::TEXT,
        v_snapshot,
        OLD.ip,
        NOW() AT TIME ZONE 'UTC'
    );

    -- Retorno el registro OLD para permitir que la eliminación en la tabla origen culmine exitosamente
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_deleted_blacklist_vault ON blacklist_entries;
CREATE TRIGGER trg_audit_deleted_blacklist_vault
AFTER DELETE ON blacklist_entries
FOR EACH ROW
EXECUTE FUNCTION fn_trg_audit_blacklist_deletion();


-- =====================================================================================
-- 2. TRIGGER 2: SANITIZACIÓN, AUTO-CLASIFICACIÓN Y DEFENSA ANTI-BLOQUEO RFC 1918
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Prevención de Denegación de Servicio Autoinfligida y Calidad de Datos CTI
-- OBJETIVO: Sanitizar cadenas de texto de IPs, impedir inserción de rangos RFC 1918 / Loopback
--           y clasificar el estado ('Bloqueada' / 'Monitoreada') según el threat_score.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Implemento este trigger BEFORE INSERT OR UPDATE sobre blacklist_entries como segunda línea
-- de defensa profunda en el motor. Limpio espacios en blanco alrededor de la dirección IP,
-- convierto la cadena al tipo nativo INET para comprobar su sintaxis, rechazo de inmediato cualquier
-- intento de bloquear IPs privadas (RFC 1918), interfaces de loopback o servidores DNS públicos,
-- y ajusto el estado a 'Bloqueada' si el puntaje supera 70 o 'Monitoreada' en caso contrario."
-- =====================================================================================

CREATE OR REPLACE FUNCTION fn_trg_sanitize_and_validate_blacklist_ip()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro la variable donde validaré sintácticamente la dirección IP como tipo de red nativo
    v_inet INET;
BEGIN
    -- Sanitizo la entrada eliminando espacios en blanco accidentales en los extremos
    NEW.ip := BTRIM(NEW.ip);

    -- Intento convertir la cadena al tipo INET; si la sintaxis es inválida capturo la excepción
    BEGIN
        v_inet := NEW.ip::INET;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Error de Integridad CTI: "%" no es una dirección IPv4/IPv6 válida.', NEW.ip
            USING ERRCODE = '22023';
    END;

    -- Compruebo si la dirección IP pertenece a redes privadas RFC 1918, loopback o infraestructura DNS
    IF v_inet <<= '127.0.0.0/8'::INET
       OR v_inet <<= '10.0.0.0/8'::INET
       OR v_inet <<= '172.16.0.0/12'::INET
       OR v_inet <<= '192.168.0.0/16'::INET
       OR host(v_inet) IN ('8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1', '9.9.9.9') THEN
        RAISE EXCEPTION 'Política de Seguridad SOC: La IP "%" pertenece a infraestructura protegida (RFC 1918 / Loopback / DNS) y no puede bloquearse.', NEW.ip
            USING ERRCODE = 'P0001';
    END IF;

    -- Asigno automáticamente la familia del protocolo (IPv6 o IPv4)
    NEW.ip_type := CASE WHEN family(v_inet) = 6 THEN 'IPv6' ELSE 'IPv4' END;

    -- Infiero el estado de la regla de bloqueo en función del umbral de severidad (threat_score > 70)
    NEW.status := CASE WHEN NEW.threat_score > 70 THEN 'Bloqueada' ELSE 'Monitoreada' END;

    -- Actualizo la marca temporal de modificación a tiempo universal coordinado (UTC)
    NEW.updated_at := NOW() AT TIME ZONE 'UTC';

    -- Si se trata de una inserción nueva y no traía fecha de creación, la inicializo
    IF TG_OP = 'INSERT' AND NEW.created_at IS NULL THEN
        NEW.created_at := NOW() AT TIME ZONE 'UTC';
    END IF;

    -- Retorno el registro sanitizado y validado para que se persista en la tabla
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sanitize_and_validate_blacklist_ip ON blacklist_entries;
CREATE TRIGGER trg_sanitize_and_validate_blacklist_ip
BEFORE INSERT OR UPDATE ON blacklist_entries
FOR EACH ROW
EXECUTE FUNCTION fn_trg_sanitize_and_validate_blacklist_ip();


-- =====================================================================================
-- 3. TRIGGER 3: AUDITORÍA AUTOMÁTICA DE CAMBIOS CRÍTICOS DE SEGURIDAD EN USUARIOS
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Gobernanza de Cuentas y Control de Acceso (Users & Identity)
-- OBJETIVO: Auditar en audit_logs de forma no eludible cualquier inserción, modificación de estado
--           o eliminación física de usuarios del sistema HoneyMetrics.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Construyo este trigger AFTER INSERT OR UPDATE OR DELETE sobre la tabla users para garantizar
-- trazabilidad absoluta ante auditorías externas. Registro la creación de cada usuario, audito
-- exclusivamente cuando se modifican campos sensibles (rol, activación, 2FA, rotación de clave o email),
-- y capturo los datos de la cuenta que fue eliminada para que nunca exista pérdida de evidencia forense."
-- =====================================================================================

CREATE OR REPLACE FUNCTION fn_trg_audit_user_security_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Caso 1: Inserción de un nuevo usuario en la base de datos
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (
            actor_user_id, actor_email, action, entity_name, entity_id, details, created_at
        ) VALUES (
            NEW.id,
            NEW.email,
            'USER_ACCOUNT_CREATED_DB',
            'users',
            NEW.id::TEXT,
            json_build_object(
                'email', NEW.email,
                'role_id', NEW.role_id,
                'is_active', NEW.is_active,
                'must_change_password', NEW.must_change_password
            ),
            NOW() AT TIME ZONE 'UTC'
        );
        RETURN NEW;

    -- Caso 2: Modificación de un usuario existente
    ELSIF TG_OP = 'UPDATE' THEN
        -- Compruebo si alguno de los atributos de seguridad críticos ha cambiado entre OLD y NEW
        IF OLD.role_id IS DISTINCT FROM NEW.role_id
           OR OLD.is_active IS DISTINCT FROM NEW.is_active
           OR OLD.is_mfa_enabled IS DISTINCT FROM NEW.is_mfa_enabled
           OR OLD.hashed_password IS DISTINCT FROM NEW.hashed_password
           OR OLD.email IS DISTINCT FROM NEW.email THEN

            INSERT INTO audit_logs (
                actor_user_id, actor_email, action, entity_name, entity_id, details, created_at
            ) VALUES (
                NEW.id,
                NEW.email,
                'USER_SECURITY_STATE_MODIFIED_DB',
                'users',
                NEW.id::TEXT,
                json_build_object(
                    'old_role_id', OLD.role_id, 'new_role_id', NEW.role_id,
                    'old_is_active', OLD.is_active, 'new_is_active', NEW.is_active,
                    'old_mfa_enabled', OLD.is_mfa_enabled, 'new_mfa_enabled', NEW.is_mfa_enabled,
                    'password_rotated', (OLD.hashed_password IS DISTINCT FROM NEW.hashed_password),
                    'old_email', OLD.email, 'new_email', NEW.email
                ),
                NOW() AT TIME ZONE 'UTC'
            );
        END IF;
        RETURN NEW;

    -- Caso 3: Eliminación física de un usuario
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (
            actor_user_id, actor_email, action, entity_name, entity_id, details, created_at
        ) VALUES (
            NULL,
            OLD.email,
            'USER_ACCOUNT_DELETED_DB',
            'users',
            OLD.id::TEXT,
            json_build_object(
                'deleted_user_id', OLD.id,
                'deleted_email', OLD.email,
                'role_id', OLD.role_id,
                'was_mfa_enabled', OLD.is_mfa_enabled
            ),
            NOW() AT TIME ZONE 'UTC'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_user_security_changes ON users;
CREATE TRIGGER trg_audit_user_security_changes
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_trg_audit_user_security_changes();


-- =====================================================================================
-- 4. TRIGGER 4: AUDITORÍA DE EVENTOS DE SEGURIDAD TRAS MODIFICACIÓN DE PERFIL DE USUARIO
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Control de Acceso y Gestión de Identidades (IAM SOC)
-- OBJETIVO: Detectar cambios sensibles en role_id, is_active o is_mfa_enabled tras un UPDATE
--           en la tabla users e insertar una entrada descriptiva estructurada en audit_logs.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-03
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Diseño este trigger AFTER UPDATE sobre la tabla users para vigilar alteraciones en el perfil de
-- privilegios y autenticación de los usuarios. Cuando se modifica el rol (role_id), la activación (is_active)
-- o la configuración de segundo factor (is_mfa_enabled), genero una entrada en audit_logs describiendo
-- el cambio con detalle forense estructurado en JSON, asegurando no repudio y trazabilidad institucional."
-- =====================================================================================

CREATE OR REPLACE FUNCTION fn_trg_audit_user_security_events()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Compruebo si cambiaron atributos de seguridad de primer orden: rol, estado activo o 2FA
    IF OLD.role_id IS DISTINCT FROM NEW.role_id
       OR OLD.is_active IS DISTINCT FROM NEW.is_active
       OR OLD.is_mfa_enabled IS DISTINCT FROM NEW.is_mfa_enabled THEN

        INSERT INTO audit_logs (
            actor_user_id,
            actor_email,
            action,
            entity_name,
            entity_id,
            details,
            created_at
        ) VALUES (
            NEW.id,
            NEW.email,
            'USER_SECURITY_EVENTS_AUDIT',
            'users',
            NEW.id::TEXT,
            json_build_object(
                'event_trigger', 'trg_audit_user_security_events',
                'user_email', NEW.email,
                'role_changed', (OLD.role_id IS DISTINCT FROM NEW.role_id),
                'old_role_id', OLD.role_id,
                'new_role_id', NEW.role_id,
                'active_changed', (OLD.is_active IS DISTINCT FROM NEW.is_active),
                'old_is_active', OLD.is_active,
                'new_is_active', NEW.is_active,
                'mfa_changed', (OLD.is_mfa_enabled IS DISTINCT FROM NEW.is_mfa_enabled),
                'old_mfa_enabled', OLD.is_mfa_enabled,
                'new_mfa_enabled', NEW.is_mfa_enabled
            ),
            NOW() AT TIME ZONE 'UTC'
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_user_security_events ON users;
CREATE TRIGGER trg_audit_user_security_events
AFTER UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_trg_audit_user_security_events();


-- =====================================================================================
-- 5. TRIGGER 5: SALVAGUARDA ANTI-BLOQUEO ADMINISTRATIVO (PREVENCIÓN DE SELF-LOCKOUT)
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Gobernanza de Cuentas y Prevención de Denegación de Servicio Administrativa
-- OBJETIVO: Garantizar la invariante de disponibilidad que impide dejar al sistema sin al menos
--           un usuario con rol 'Administrador' activo, lanzando excepción P0003 ante intentos de violación.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-03
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Implemento este trigger BEFORE UPDATE OR DELETE sobre users como salvaguarda crítica del sistema.
-- Determino si la operación intenta desactivar, reasignar de rol o eliminar físicamente a un usuario
-- con rol 'Administrador'. Si tras dicha operación el conteo de administradores activos descendería
-- a cero, aborto la transacción lanzando la excepción 'P0003', evitando el bloqueo total del sistema."
-- =====================================================================================

CREATE OR REPLACE FUNCTION fn_trg_prevent_admin_self_lockout()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro las variables para identificar el rol Administrador y contabilizar los administradores restantes
    v_admin_role_id INT;
    v_active_admins_remaining INT;
BEGIN
    -- Localizo el identificador asignado al rol canónico Administrador
    SELECT id INTO v_admin_role_id
    FROM roles
    WHERE LOWER(BTRIM(name)) = 'administrador';

    -- Si no existe dicho rol en la base de datos, no aplico restricción
    IF v_admin_role_id IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- Verifico si la fila sobre la que se opera corresponde a un Administrador activo
    IF OLD.role_id = v_admin_role_id AND OLD.is_active = TRUE THEN
        IF TG_OP = 'DELETE' THEN
            -- Se intenta eliminar el registro: cuento cuántos Administradores activos quedarían
            SELECT COUNT(*) INTO v_active_admins_remaining
            FROM users
            WHERE role_id = v_admin_role_id
              AND is_active = TRUE
              AND id <> OLD.id;

            IF v_active_admins_remaining = 0 THEN
                RAISE EXCEPTION 'Gobernanza de Seguridad SOC (P0003): No es posible eliminar al último Administrador activo del sistema (prevención de auto-bloqueo catastrófico).'
                    USING ERRCODE = 'P0003';
            END IF;
            RETURN OLD;

        ELSIF TG_OP = 'UPDATE' THEN
            -- Se intenta actualizar: verifico si se desactiva al usuario o se le cambia el rol
            IF (NEW.is_active = FALSE) OR (NEW.role_id <> v_admin_role_id) THEN
                SELECT COUNT(*) INTO v_active_admins_remaining
                FROM users
                WHERE role_id = v_admin_role_id
                  AND is_active = TRUE
                  AND id <> OLD.id;

                IF v_active_admins_remaining = 0 THEN
                    RAISE EXCEPTION 'Gobernanza de Seguridad SOC (P0003): No es posible desactivar ni revocar privilegios al último Administrador activo del sistema (prevención de auto-bloqueo catastrófico).'
                        USING ERRCODE = 'P0003';
                END IF;
            END IF;
            RETURN NEW;
        END IF;
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_admin_self_lockout ON users;
CREATE TRIGGER trg_prevent_admin_self_lockout
BEFORE UPDATE OR DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION fn_trg_prevent_admin_self_lockout();


-- =====================================================================================
-- 6. PROCEDIMIENTO ALMACENADO 1: PURGA Y MANTENIMIENTO DE TOKENS Y EXPORTACIONES
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Tareas de Mantenimiento y Purgas Automáticas del Sistema
-- OBJETIVO: Purgar tokens revocados expirados de revoked_tokens, marcar exportaciones antiguas
--           como 'Expirado' en log_exports y registrar el resultado de la operación en audit_logs.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Diseño este procedimiento almacenado para automatizar la higiene de datos sensibles. Primero,
-- elimino de revoked_tokens todos los tokens JWT cuya fecha natural de expiración ya transcurrió;
-- segundo, actualizo el estado a 'Expirado' en las solicitudes de exportación que sobrepasan la
-- ventana de retención (7 días por defecto); finalmente, inserto en audit_logs el número exacto
-- de filas depuradas."
-- =====================================================================================

CREATE OR REPLACE PROCEDURE sp_archive_and_purge_expired_exports_and_tokens(
    IN p_retention_days INT DEFAULT 7
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro los contadores de filas afectadas para cada operación de depuración
    v_purged_tokens INT := 0;
    v_expired_exports INT := 0;
BEGIN
    -- 1. Elimino tokens revocados cuyo tiempo de expiración ya caducó
    DELETE FROM revoked_tokens
    WHERE expires_at IS NOT NULL
      AND expires_at < (NOW() AT TIME ZONE 'UTC');
    GET DIAGNOSTICS v_purged_tokens = ROW_COUNT;

    -- 2. Marco como expiradas las solicitudes de exportación antiguas
    UPDATE log_exports
    SET status = 'Expirado',
        updated_at = (NOW() AT TIME ZONE 'UTC')
    WHERE created_at < ((NOW() AT TIME ZONE 'UTC') - make_interval(days => p_retention_days))
      AND status IN ('Listo', 'Pendiente de Aprobación', 'Procesando');
    GET DIAGNOSTICS v_expired_exports = ROW_COUNT;

    -- 3. Inserto el registro de auditoría con el balance de filas depuradas
    INSERT INTO audit_logs (
        actor_user_id, actor_email, action, entity_name, entity_id, details, created_at
    ) VALUES (
        NULL,
        'SYSTEM_MAINTENANCE_SP',
        'SP_PURGE_TOKENS_AND_EXPORTS',
        'revoked_tokens,log_exports',
        'BATCH',
        json_build_object(
            'retention_days', p_retention_days,
            'purged_revoked_tokens', v_purged_tokens,
            'expired_log_exports', v_expired_exports
        ),
        NOW() AT TIME ZONE 'UTC'
    );
END;
$$;


-- =====================================================================================
-- 7. PROCEDIMIENTO ALMACENADO 2: ESCALAMIENTO Y CONSOLIDACIÓN DE AMENAZAS EN BLACKLIST
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Threat Intelligence Center (CTI) y Respuesta a Incidentes
-- OBJETIVO: Actualizar el nivel de riesgo de una IP atacante, recalcular su estado operativo,
--           anexar trazabilidad textual en el campo notes y auditar el evento en audit_logs.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Construyo este procedimiento almacenado para permitir al equipo SOC consolidar evidencia de
-- ataque. Busco la IP especificada en blacklist_entries, valido que exista, delimito el nuevo puntaje
-- entre 0 y 100 con funciones matemáticas LEAST y GREATEST, anexo una nota histórica con fecha UTC
-- al historial existente, actualizo el estado a 'Bloqueada' o 'Monitoreada' y registro la auditoría."
-- =====================================================================================

CREATE OR REPLACE PROCEDURE sp_escalate_and_consolidate_blacklist_threat(
    IN p_ip VARCHAR(45),
    IN p_new_score INT,
    IN p_analyst_note TEXT,
    IN p_actor_user_id INT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro las variables necesarias para rescatar el estado anterior y calcular el nuevo
    v_entry_id INT;
    v_old_score INT;
    v_old_status VARCHAR(30);
    v_new_status VARCHAR(30);
BEGIN
    -- Busco la IP en la tabla de lista negra limpiando espacios
    SELECT id, threat_score, status
    INTO v_entry_id, v_old_score, v_old_status
    FROM blacklist_entries
    WHERE ip = BTRIM(p_ip);

    -- Compruebo si la IP fue localizada; si no existe, lanzo una excepción formal
    IF NOT FOUND THEN
        RAISE EXCEPTION 'La IP "%" no existe en blacklist_entries.', p_ip
            USING ERRCODE = 'P0002';
    END IF;

    -- Calculo el nuevo estado operativo con base en el umbral de severidad de la cátedra
    v_new_status := CASE WHEN p_new_score > 70 THEN 'Bloqueada' ELSE 'Monitoreada' END;

    -- Aplico la actualización acotando el puntaje al rango [0, 100] y concatenando la bitácora
    UPDATE blacklist_entries
    SET threat_score = LEAST(100, GREATEST(0, p_new_score)),
        status = v_new_status,
        notes = COALESCE(notes || E'\n', '') || '[' || to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') || ' UTC] ' || COALESCE(p_analyst_note, 'Actualización por SP'),
        updated_at = (NOW() AT TIME ZONE 'UTC')
    WHERE id = v_entry_id;

    -- Registro la acción en la tabla general de auditoría para preservación de evidencia
    INSERT INTO audit_logs (
        actor_user_id, actor_email, action, entity_name, entity_id, details, ip_address, created_at
    ) VALUES (
        p_actor_user_id,
        'SOC_ANALYST_SP',
        'SP_BLACKLIST_THREAT_ESCALATED',
        'blacklist_entries',
        v_entry_id::TEXT,
        json_build_object(
            'ip', p_ip,
            'old_score', v_old_score,
            'new_score', p_new_score,
            'old_status', v_old_status,
            'new_status', v_new_status,
            'note_added', p_analyst_note
        ),
        p_ip,
        NOW() AT TIME ZONE 'UTC'
    );
END;
$$;


-- =====================================================================================
-- 8. PROCEDIMIENTO ALMACENADO 3: ROTACIÓN FORZOSA DE CREDENCIALES Y AUDITORÍA POR ROL
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Protocolo de Contención de Incidentes de Seguridad de la Información
-- OBJETIVO: Forzar el cambio de contraseña a todos los usuarios de un rol específico,
--           invalidar sus sesiones activas incrementando auth_version y auditar la acción.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-01
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Diseño este procedimiento almacenado para respuesta inmediata ante sospecha de fuga de credenciales.
-- Consulto el identificador del rol según su nombre normalizado, compruebo su existencia, y en una
-- sola sentencia atómica activo must_change_password = TRUE e incremento auth_version en todos los
-- usuarios activos de dicho rol para invalidar sus tokens JWT vigentes, dejando constancia en audit_logs."
-- =====================================================================================

CREATE OR REPLACE PROCEDURE sp_enforce_role_password_rotation_and_audit(
    IN p_role_name VARCHAR(50),
    IN p_reason TEXT DEFAULT 'Rotación preventiva por política de seguridad SOC'
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro las variables para almacenar el identificador del rol y el total de usuarios afectados
    v_role_id INT;
    v_affected_users INT := 0;
BEGIN
    -- Localizo el identificador del rol objetivo ignorando mayúsculas y espacios
    SELECT id INTO v_role_id
    FROM roles
    WHERE LOWER(BTRIM(name)) = LOWER(BTRIM(p_role_name));

    -- Compruebo si el rol existe en el catálogo; de lo contrario aborto con excepción
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El rol "%" no existe en el catálogo de roles.', p_role_name
            USING ERRCODE = 'P0002';
    END IF;

    -- Actualizo los usuarios activos del rol: forzando cambio de clave e invalidando JWTs
    UPDATE users
    SET must_change_password = TRUE,
        auth_version = COALESCE(auth_version, 0) + 1,
        updated_at = (NOW() AT TIME ZONE 'UTC')
    WHERE role_id = v_role_id
      AND is_active = TRUE;

    -- Obtengo la cantidad exacta de filas actualizadas
    GET DIAGNOSTICS v_affected_users = ROW_COUNT;

    -- Registro el incidente y la rotación aplicada en la bitácora de auditoría
    INSERT INTO audit_logs (
        actor_user_id, actor_email, action, entity_name, entity_id, details, created_at
    ) VALUES (
        NULL,
        'SECURITY_GOVERNANCE_SP',
        'SP_ROLE_PASSWORD_ROTATION_ENFORCED',
        'users',
        v_role_id::TEXT,
        json_build_object(
            'target_role', p_role_name,
            'affected_active_users', v_affected_users,
            'reason', p_reason
        ),
        NOW() AT TIME ZONE 'UTC'
    );
END;
$$;


-- =====================================================================================
-- 9. PROCEDIMIENTO ALMACENADO 4: ESCALAMIENTO MASIVO DE AMENAZAS POR UMBRAL DE RIESGO
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Threat Intelligence Center (CTI) y Automatización de Mitigación Masiva
-- OBJETIVO: Escalar a threat_score = 100 y status = 'Bloqueada' todas las IPs en blacklist_entries
--           que superen o igualen el umbral p_min_score, devolviendo el total en p_updated_count.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-03
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Diseño este procedimiento almacenado para respuesta automatizada a gran escala ante ciberataques coordinados.
-- Recibo el umbral mínimo p_min_score, ejecuto una actualización masiva sobre blacklist_entries fijando
-- threat_score = 100 y status = 'Bloqueada', capturo el número de registros afectados mediante GET DIAGNOSTICS
-- y devuelvo el conteo en el parámetro INOUT p_updated_count, auditando la operación en audit_logs."
-- =====================================================================================

CREATE OR REPLACE PROCEDURE sp_bulk_escalate_threat_scores(
    IN p_min_score INT,
    INOUT p_updated_count INT DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Declaro la variable donde capturaré las filas afectadas por el UPDATE
    v_rows INT := 0;
BEGIN
    -- Actualizo masivamente las IPs que igualan o superan el umbral establecido
    UPDATE blacklist_entries
    SET threat_score = 100,
        status = 'Bloqueada',
        notes = COALESCE(notes || E'\n', '') || '[' || to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') || ' UTC] Escalamiento masivo por SP (umbral >= ' || p_min_score::TEXT || ')',
        updated_at = (NOW() AT TIME ZONE 'UTC')
    WHERE threat_score >= p_min_score;

    -- Obtengo el total de filas impactadas por la sentencia DML
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    p_updated_count := v_rows;

    -- Inserto la traza de auditoría con la evidencia del escalamiento masivo
    INSERT INTO audit_logs (
        actor_user_id,
        actor_email,
        action,
        entity_name,
        entity_id,
        details,
        created_at
    ) VALUES (
        NULL,
        'SOC_AUTOMATION_SP',
        'SP_BULK_ESCALATE_THREAT_SCORES',
        'blacklist_entries',
        'BULK',
        json_build_object(
            'min_score_threshold', p_min_score,
            'updated_count', p_updated_count
        ),
        NOW() AT TIME ZONE 'UTC'
    );
END;
$$;


-- =====================================================================================
-- 10. PROCEDIMIENTO ALMACENADO 5: GENERACIÓN DE RESUMEN DE CUMPLIMIENTO Y POSTURA SOC
-- =====================================================================================
-- ENCABEZADO FORMAL DOCENTE:
-- APLICACIÓN: Módulo de Reportes de Cumplimiento SOC y Métricas CTI
-- OBJETIVO: Consolidar y retornar mediante parámetros INOUT las métricas críticas del estado
--           de seguridad del sistema: usuarios activos, adopción de MFA, IPs bloqueadas y bóveda.
-- AUTORES: Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis
-- FECHA: 2026-11-03
--
-- EXPLICACIÓN EN PRIMERA PERSONA:
-- "Construyo este procedimiento almacenado para facilitar la generación de tableros ejecutivos e informes
-- de auditoría forense. Mediante consultas agregadas sobre las tablas users, blacklist_entries y blacklist_audit_vault,
-- rescato los cuatro indicadores clave de postura defensiva y los asigno directamente a sus respectivos
-- parámetros INOUT, persistiendo la captura histórica del snapshot en audit_logs."
-- =====================================================================================

CREATE OR REPLACE PROCEDURE sp_generate_soc_compliance_summary(
    INOUT p_active_users INT DEFAULT 0,
    INOUT p_mfa_enabled_users INT DEFAULT 0,
    INOUT p_blocked_ips INT DEFAULT 0,
    INOUT p_vault_records INT DEFAULT 0
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Contabilizo el total de usuarios con acceso activo al sistema
    SELECT COUNT(*) INTO p_active_users
    FROM users
    WHERE is_active = TRUE;

    -- 2. Contabilizo los usuarios que tienen habilitado el factor de autenticación robusto (MFA)
    SELECT COUNT(*) INTO p_mfa_enabled_users
    FROM users
    WHERE is_active = TRUE
      AND is_mfa_enabled = TRUE;

    -- 3. Contabilizo el volumen de amenazas mitigadas bajo regla activa 'Bloqueada'
    SELECT COUNT(*) INTO p_blocked_ips
    FROM blacklist_entries
    WHERE status = 'Bloqueada';

    -- 4. Contabilizo la totalidad de registros históricos preservados en la bóveda inmutable
    SELECT COUNT(*) INTO p_vault_records
    FROM blacklist_audit_vault;

    -- 5. Registro la consulta de cumplimiento en la bitácora de auditoría
    INSERT INTO audit_logs (
        actor_user_id,
        actor_email,
        action,
        entity_name,
        entity_id,
        details,
        created_at
    ) VALUES (
        NULL,
        'SOC_COMPLIANCE_SP',
        'SP_GENERATE_SOC_COMPLIANCE_SUMMARY',
        'compliance_summary',
        'SYSTEM',
        json_build_object(
            'active_users', p_active_users,
            'mfa_enabled_users', p_mfa_enabled_users,
            'blocked_ips', p_blocked_ips,
            'vault_records', p_vault_records
        ),
        NOW() AT TIME ZONE 'UTC'
    );
END;
$$;


-- =====================================================================================
-- 11. SCRIPT DE PRUEBAS COMPLETO Y REPRODUCIBLE PARA DBEAVER (EVIDENCIA DOCENTE)
-- =====================================================================================
-- Conectarse a 127.0.0.1:5433 (Base de datos: honeymetrics_v2, usuario: postgres)
-- y ejecutar en orden los siguientes bloques de prueba:
--
-- PASO 1: Probar Trigger 2 (Sanitización y auto-clasificación de amenaza):
-- INSERT INTO blacklist_entries (ip, country, threat_score, category, status, notes, created_at, updated_at)
-- VALUES ('  185.220.101.77  ', 'Germany', 88, 'APT', 'Monitoreada', 'Prueba de inserción inicial', NOW(), NOW());
-- SELECT id, ip, ip_type, threat_score, status, notes FROM blacklist_entries WHERE ip = '185.220.101.77';
--
-- PASO 2: Probar defensa de Trigger 2 contra IPs privadas (debe rechazar con excepción):
-- -- INSERT INTO blacklist_entries (ip, country, threat_score, category, status, notes, created_at, updated_at)
-- -- VALUES ('192.168.1.50', 'LAN', 90, 'Test', 'Monitoreada', 'Debe fallar', NOW(), NOW());
--
-- PASO 3: Probar Procedimiento Almacenado 2 (Escalamiento y Bitácora de Amenaza):
-- CALL sp_escalate_and_consolidate_blacklist_threat('185.220.101.77', 96, 'Confirmado ataque persistente contra honeypot SSH');
-- SELECT id, ip, threat_score, status, notes FROM blacklist_entries WHERE ip = '185.220.101.77';
--
-- PASO 4: Probar Trigger 1 (Bóveda Forense al dar de baja la IP):
-- DELETE FROM blacklist_entries WHERE ip = '185.220.101.77';
-- SELECT id, original_ip, threat_score, full_record_json, deleted_at FROM blacklist_audit_vault ORDER BY deleted_at DESC LIMIT 1;
--
-- PASO 5: Probar Procedimientos Almacenados 1 y 3 + Trigger 3:
-- CALL sp_archive_and_purge_expired_exports_and_tokens(7);
-- CALL sp_enforce_role_password_rotation_and_audit('Analista', 'Simulacro preventivo de seguridad');
--
-- PASO 6: Probar Trigger 4 (Auditoría de eventos de seguridad en actualización de usuario):
-- DO $$
-- DECLARE
--     v_test_uid INT;
-- BEGIN
--     SELECT id INTO v_test_uid FROM users ORDER BY id LIMIT 1;
--     IF v_test_uid IS NOT NULL THEN
--         UPDATE users SET is_mfa_enabled = NOT is_mfa_enabled WHERE id = v_test_uid;
--         UPDATE users SET is_mfa_enabled = NOT is_mfa_enabled WHERE id = v_test_uid;
--         RAISE NOTICE '>>> Trigger 4 probado: Se generó evento de auditoría para usuario ID %', v_test_uid;
--     END IF;
-- END;
-- $$;
--
-- PASO 7: Probar Trigger 5 (Prevención de Auto-Bloqueo de Administrador - Excepción P0003):
-- DO $$
-- DECLARE
--     v_admin_role_id INT;
-- BEGIN
--     SELECT id INTO v_admin_role_id FROM roles WHERE LOWER(BTRIM(name)) = 'administrador';
--     BEGIN
--         -- Intento de desactivar a todos los administradores activos: debe ser bloqueado por Trigger 5
--         UPDATE users SET is_active = FALSE WHERE role_id = v_admin_role_id;
--         RAISE EXCEPTION 'Fallo de prueba: Trigger 5 debió haber impedido la desactivación de administradores.';
--     EXCEPTION
--         WHEN SQLSTATE 'P0003' THEN
--             RAISE NOTICE '>>> ÉXITO: Trigger 5 interceptó la operación e impidió el auto-bloqueo (Excepción P0003 capturada).';
--         WHEN OTHERS THEN
--             RAISE NOTICE '>>> Capturada otra excepción: % (SQLSTATE: %)', SQLERRM, SQLSTATE;
--     END;
-- END;
-- $$;
--
-- PASO 8: Probar Procedimiento Almacenado 4 (Escalamiento masivo de amenazas con parámetro INOUT):
-- DO $$
-- DECLARE
--     v_count INT := 0;
-- BEGIN
--     CALL sp_bulk_escalate_threat_scores(70, v_count);
--     RAISE NOTICE '>>> SP 4 Ejecutado: Total registros escalados masivamente = %', v_count;
-- END;
-- $$;
--
-- PASO 9: Probar Procedimiento Almacenado 5 (Resumen de cumplimiento SOC con parámetros INOUT):
-- DO $$
-- DECLARE
--     v_activos INT := 0;
--     v_mfa INT := 0;
--     v_bloqueadas INT := 0;
--     v_boveda INT := 0;
-- BEGIN
--     CALL sp_generate_soc_compliance_summary(v_activos, v_mfa, v_bloqueadas, v_boveda);
--     RAISE NOTICE '>>> SP 5 Resumen SOC: Activos=%, MFA=%, IPs Bloqueadas=%, Bóveda=%',
--         v_activos, v_mfa, v_bloqueadas, v_boveda;
-- END;
-- $$;
--
-- PASO 10: Consultar la Tabla General de Auditoría (audit_logs) con toda la historia:
-- SELECT id, actor_email, action, entity_name, entity_id, details, created_at
-- FROM audit_logs
-- ORDER BY created_at DESC LIMIT 15;
--
-- PASO 11: Verificar existencia de los 5 SPs y 5 Triggers en el catálogo de PostgreSQL:
-- SELECT routine_name, routine_type
-- FROM information_schema.routines
-- WHERE routine_schema = 'public' AND routine_name LIKE 'sp_%'
-- ORDER BY routine_name;
--
-- SELECT trigger_name, event_manipulation, event_object_table
-- FROM information_schema.triggers
-- WHERE trigger_schema = 'public'
-- ORDER BY trigger_name;
-- =====================================================================================
