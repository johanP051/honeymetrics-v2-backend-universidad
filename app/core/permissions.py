"""
Matriz canónica de Roles y Scopes (PBAC - Permission-Based Access Control)
para HoneyMetrics v2 (Cátedra de Ingeniería de Software - UDEC).

Elimina el hardcodeo de nombres de roles en controladores y endpoints,
haciendo cumplir el estándar global-rbac-pbac-scopes.
"""
from typing import Dict, List, Optional

ROLES_TO_SCOPES: Dict[str, List[str]] = {
    "Administrador": [
        "dashboard:read",
        "threats:read",
        "threats:write",
        "threats:delete",
        "logs:read",
        "logs:export",
        "blacklist:read",
        "blacklist:write",
        "users:profile",
        "admin:all",
    ],
    "Analista": [
        "dashboard:read",
        "threats:read",
        "logs:read",
        "logs:export",
        "blacklist:read",
        "users:profile",
    ],
    "Consultor": [
        "dashboard:read",
        "threats:read",
        "logs:read",
        "logs:export",
        "users:profile",
    ],
    "Directivo": [
        "dashboard:read",
        "threats:read",
        "logs:read",
        "users:profile",
    ],
}

CANONICAL_EQUIVALENCES: Dict[str, str] = {
    "administrador": "Administrador",
    "superusuario": "Administrador",
    "admin": "Administrador",
    "superuser": "Administrador",
    "directivo": "Directivo",
    "directivo de t.i.": "Directivo",
    "directivo de ti": "Directivo",
    "analista": "Analista",
    "analista de datos": "Analista",
    "consultor": "Consultor",
    "consultor de ciberseguridad": "Consultor",
}


def get_scopes_for_role(role_name: Optional[str]) -> List[str]:
    """
    Retorna la lista de scopes asociados a un nombre de rol dado.
    Aplica equivalencia canónica exacta evitando falsos positivos por substrings inseguros.
    """
    if not role_name or not isinstance(role_name, str):
        return []
    normalized = role_name.strip().lower()
    if normalized in CANONICAL_EQUIVALENCES:
        canonical_key = CANONICAL_EQUIVALENCES[normalized]
        return ROLES_TO_SCOPES.get(canonical_key, [])
    # Búsqueda directa preservando mayúsculas/minúsculas de roles personalizados
    clean_original = role_name.strip()
    return ROLES_TO_SCOPES.get(clean_original, [])
