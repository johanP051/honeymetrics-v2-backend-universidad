# Clase para crear routers
from fastapi import APIRouter

from app.api.v1.endpoints.auth_endpoints import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router)

# main.py ya agrega el prefijo /api/v1 en: app.include_router(api_router, prefix=settings.API_V1_STR)

# Se agregan todas las rutas definidas en auth_endpoints.py

# ESTRUCTURA
# api_router
# └── auth_router
#     └── POST /auth/login

# Al final los prefijos se combinan: /api/v1 + /auth + /login
