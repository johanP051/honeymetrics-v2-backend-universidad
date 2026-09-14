from fastapi import APIRouter

# APIRouter es la herramienta que me permite agrupar rutas de FastAPI
# router = APIRouter(...) crea un grupo de rutas, en este caso para autenticacion
# prefix="auth/" Hace que todas las rutas de este archivo empiecen con /auth
# tags=["Authentication"] Agrupa esas rutas con el nombre Authentication en Swagger (Documentacion)

router = APIRouter(
    prefix="auth/", #
    tags=["Authentication"]
)