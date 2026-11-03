"""
Motor Central de Políticas de Contraseñas — OWASP ASVS 4.0.3 Sección V2.1.
HoneyMetrics Backend v2.0 (UDEC)
"""
import re
from typing import Optional
from app.core.domain_errors import ValidationError

# ASVS V2.1.7 - Denylist de contraseñas comunes, vulneradas o asociadas al contexto institucional/proyecto
COMMON_PASSWORDS_DENYLIST = frozenset({
    "password1234",
    "password12345",
    "123456789012",
    "1234567890123",
    "admin12345678",
    "admin123456789",
    "honeymetrics12",
    "honeymetrics2024",
    "honeymetrics2025",
    "honeymetrics2026",
    "ucundinamarca12",
    "ucundinamarca2024",
    "ucundinamarca2025",
    "ucundinamarca2026",
    "administrator1",
    "qwertyuiop12",
    "welcome123456",
    "iloveyou12345",
    "facatativa1234",
    "cundinamarca12",
})


def normalize_password(password: str) -> str:
    """
    Normaliza la contraseña colapsando secuencias de espacios consecutivos en blanco
    y recortando espacios al inicio y final según ASVS V2.1.
    """
    if not isinstance(password, str):
        return ""
    return re.sub(r"\s+", " ", password.strip())


def validate_new_password(new_password: str, current_password: Optional[str] = None) -> str:
    """
    Valida una nueva contraseña contra OWASP ASVS 4.0.3 Sección V2.1:
    - Normalización y longitud: Mínimo 12 caracteres, máximo 128 caracteres.
    - Soporte completo para caracteres Unicode imprimibles (tildes, emojis, espacios, símbolos).
    - V2.1.3: Cero reglas arbitrarias de composición obligatoria (no exige mayúsculas/números forzados).
    - V2.1.7: Denylist de contraseñas comunes/vulneradas.
    - Validación de no-repetición: no puede ser igual a la contraseña actual.
    
    Retorna la contraseña normalizada.
    """
    if not isinstance(new_password, str):
        raise ValidationError("La contraseña debe ser una cadena de texto válida.")

    normalized = normalize_password(new_password)

    # Verificación de identidad con la contraseña actual
    if current_password is not None and isinstance(current_password, str):
        norm_current = normalize_password(current_password)
        if normalized == norm_current:
            raise ValidationError("La nueva contraseña no puede ser igual a la contraseña actual.")

    # V2.1.1 - Longitud mínima de 12 caracteres y máxima de 128 caracteres
    if len(normalized) < 12:
        raise ValidationError("La contraseña debe tener al menos 12 caracteres.")

    if len(normalized) > 128:
        raise ValidationError("La contraseña no puede exceder los 128 caracteres.")

    # V2.1.7 - Denylist de contraseñas vulneradas o comunes
    if normalized.lower() in COMMON_PASSWORDS_DENYLIST:
        raise ValidationError(
            "La contraseña ingresada es demasiado común o insegura. Elija una contraseña más robusta."
        )

    # Verificación de cadenas de caracteres triviales idénticos (ej. 'aaaaaaaaaaaa')
    if len(set(normalized)) == 1:
        raise ValidationError(
            "La contraseña no puede consistir exclusivamente de un mismo carácter repetido."
        )

    return normalized
