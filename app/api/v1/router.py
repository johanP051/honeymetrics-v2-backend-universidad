from fastapi import APIRouter
from app.api.v1.endpoints import health

api_router = APIRouter()

# Registro de controladores modulares
api_router.include_router(health.router, tags=["Diagnóstico & Salud"])
