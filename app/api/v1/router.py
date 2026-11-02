"""
Enrutador Central API v1.
HoneyMetrics Backend v2.0 (UDEC)
"""
from fastapi import APIRouter

from app.api.v1.endpoints.admin_endpoints import (
    admin_users_router,
    router as admin_router,
)
from app.api.v1.endpoints.auth_endpoints import router as auth_router
from app.api.v1.endpoints.blacklist_endpoints import router as blacklist_router
from app.api.v1.endpoints.dashboard_endpoints import router as dashboard_router
from app.api.v1.endpoints.health_endpoints import router as health_router
from app.api.v1.endpoints.logs_endpoints import router as logs_router
from app.api.v1.endpoints.roles_endpoints import router as roles_router
from app.api.v1.endpoints.threats_endpoints import router as threats_router
from app.api.v1.endpoints.users_endpoints import router as users_router

api_router = APIRouter()

# Health Check Raíz (/api/v1/health)
api_router.include_router(health_router)

# Autenticación (/api/v1/auth)
api_router.include_router(auth_router)

# Logs y Telemetría Forense (/api/v1/logs)
api_router.include_router(logs_router)

# Threat Intelligence (/api/v1/threats y /api/v1/threats-center)
api_router.include_router(threats_router, prefix="/threats", tags=["Threat Intelligence"])
api_router.include_router(threats_router, prefix="/threats-center", tags=["Threat Center Telemetry"])

# Blacklist y Bóveda Forense (/api/v1/blacklist, /api/v1/threats/blacklist, /api/v1/threats-center)
api_router.include_router(blacklist_router, prefix="/blacklist", tags=["Blacklist"])
api_router.include_router(blacklist_router, prefix="/threats/blacklist", tags=["Threats Blacklist"])
api_router.include_router(blacklist_router, prefix="/threats-center", tags=["Threat Center CRUD"])

# Perfil de Usuario Propio (/api/v1/users/me)
api_router.include_router(users_router)

# Administración de Usuarios y Auditoría (/api/v1/admin y /api/v1/users)
api_router.include_router(admin_router)
api_router.include_router(admin_users_router)

# Gestión de Roles (/api/v1/roles y /api/v1/admin/roles)
api_router.include_router(roles_router, prefix="/roles", tags=["Gestión de Roles"])
api_router.include_router(roles_router, prefix="/admin/roles", tags=["Gestión de Roles (Admin)"])

# Reportes Ejecutivos (/api/v1/dashboard/report/executive)
api_router.include_router(dashboard_router)
