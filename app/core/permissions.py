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
        "logs:read",
        "logs:export",
        "blacklist:read",
        "blacklist:write",
        "admin:all",
    ],
    "Analista": [
        "dashboard:read",
        "threats:read",
        "logs:read",
        "logs:export",
        "blacklist:read",
    ],
    "Consultor": [
        "dashboard:read",
        "threats:read",
        "logs:read",
        "logs:export",
    ],
    "Directivo": [
        "dashboard:read",
    ],
}


def get_scopes_for_role(role_name: Optional[str]) -> List[str]:
    """Retorna la lista de scopes asociados a un nombre de rol dado."""
    if not role_name:
        return []
    # Normalización para compatibilidad con seeds
    normalized = role_name.strip()
    if normalized.lower() in ("admin", "administrador"):
        return ROLES_TO_SCOPES.get("Administrador", [])
    if normalized.lower() == "analista":
        return ROLES_TO_SCOPES.get("Analista", [])
    if normalized.lower() == "consultor":
        return ROLES_TO_SCOPES.get("Consultor", [])
    if normalized.lower() == "directivo":
        return ROLES_TO_SCOPES.get("Directivo", [])
    return ROLES_TO_SCOPES.get(normalized, [])
