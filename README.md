# 🛡️ HoneyMetrics v2 — Backend Universitario

> **Cátedra de Ingeniería de Software — Universidad de Cundinamarca (UDEC Facatativá)**  
> **Integrantes:** Johan Sebastián Posada Beltrán & Juan Pablo Fonseca Celis  
> **Tecnología:** Python 3.12 + FastAPI (Asíncrono) + PostgreSQL 16 + Docker Multi-Etapa  

---

## 📑 Tabla de Contenido (Índice de Navegación)
1. [Visión General del Proyecto](#-visión-general-del-proyecto)
2. [Estructura del Proyecto y Mapa de Capas](#-estructura-del-proyecto-y-mapa-de-capas)
3. [Guía de Puesta en Marcha con Docker](#-guía-de-puesta-en-marcha-con-docker)
   - [Modo 1: Desarrollo Local con Live-Reload](#modo-1-desarrollo-local-con-live-reload)
   - [Modo 2: Desarrollo con Túnel Cloudflare (Acceso Remoto)](#modo-2-desarrollo-con-túnel-cloudflare-acceso-remoto)
   - [Modo 3: Despliegue Endurecido (Staging / Producción)](#modo-3-despliegue-endurecido-staging--producción)
4. [Configuración de Variables de Entorno (.env)](#-configuración-de-variables-de-entorno-env)
5. [Ejecución Alternativa en Host (.venv Local)](#-ejecución-alternativa-en-host-venv-local)
6. [Poblado de Base de Datos (Seeds) y Pruebas Unitarias](#-poblado-de-base-de-datos-seeds-y-pruebas-unitarias)
7. [Documentación Interactiva (Swagger / OpenAPI)](#-documentación-interactiva-swagger--openapi)
8. [Biblioteca de Documentación Técnica Avanzada (docs/)](#-biblioteca-de-documentación-técnica-avanzada-docs)

---

## 📖 Visión General del Proyecto

HoneyMetrics v2 es una plataforma backend de **Inteligencia de Amenazas Cibernéticas (Cyber Threat Intelligence - CTI)** orientada a la ingesta, normalización y análisis de telemetría proveniente de señuelos (Honeypots). 

Este repositorio constituye la base técnica para la entrega iterativa de **Sprints semanales** bajo el marco ágil **Scrum**, implementando una arquitectura multicapa desacoplada y principios de **Clean Architecture**.

---

## 🗺️ Estructura del Proyecto y Mapa de Capas

El código está organizado bajo una estricta separación de responsabilidades:

```text
honeymetrics-v2-backend-universidad/
├── app/                        # Código fuente de la aplicación
│   ├── api/v1/endpoints/       # CONTROLADORES: Thin Controllers (<15 líneas), ruteo HTTP
│   ├── api/v1/router.py        # Centralizador y prefijo de rutas (/api/v1)
│   ├── core/                   # 12-FACTOR: Settings (Pydantic), constantes y seguridad
│   ├── db/                     # CONECTIVIDAD: Sesiones SQLAlchemy y engine asíncrono
│   ├── models/                 # ENTIDADES: Modelos declarativos ORM para la base de datos
│   ├── schemas/                # DTOs: Contratos Request/Response validados con Pydantic v2
│   ├── services/               # SERVICE LAYER: Lógica de negocio pura (independiente de HTTP)
│   ├── utils/                  # UTILIDADES: Funciones puras y helpers transversales
│   └── main.py                 # FACTORY: Instancia FastAPI, CORS y ciclo de vida (lifespan)
├── docs/                       # Documentación técnica profunda (wiki navegable)
├── scripts/                    # Scripts de administración, seeds y automatización CLI
├── tests/                      # Suite de pruebas automatizadas con Pytest
├── Dockerfile                  # Construcción multi-etapa con usuario non-root (appuser)
├── docker-compose.yml          # Servicios base (FastAPI + PostgreSQL 16)
├── docker-compose.override.yml # Configuración de desarrollo (puertos host, live-reload)
├── docker-compose.prod.yml     # Configuración de producción (sin puertos de BD expuestos)
├── .env.example                # Plantilla documentada de variables de entorno
└── requirements.txt            # Dependencias fijadas del proyecto
```

---

## 🐳 Guía de Puesta en Marcha con Docker

El proyecto utiliza la técnica de **Compose Overrides** para desacoplar el desarrollo de la producción sin duplicar configuraciones.

### Modo 1: Desarrollo Local con Live-Reload
Ideal para programar día a día. Cualquier cambio en el código fuente de `app/` se refleja automáticamente en milisegundos gracias al montaje de volúmenes:

```bash
# 1. Asegurar archivo de entorno
cp .env.example .env

# 2. Levantar los contenedores (Docker lee automáticamente docker-compose.yml + docker-compose.override.yml)
docker compose up -d

# 3. Inspeccionar logs en tiempo real
docker compose logs -f api
```
- **API en host:** `http://localhost:8001` (o `http://localhost:8001/api/v1/health`)
- **PostgreSQL en host:** `localhost:5433` (mapeado para no colisionar con el 5432 habitual)
- **Documentación Swagger:** `http://localhost:8001/docs`

---

### Modo 2: Desarrollo con Túnel Cloudflare (Acceso Remoto)
Ideal para realizar pruebas desde la red Wi-Fi de la universidad, o para que tu compañero de equipo consuma la API desde su casa sin abrir puertos en el router:

```bash
# 1. Coloca tu token de túnel en el archivo .env:
# CLOUDFLARE_TUNNEL_TOKEN="eyJh..."

# 2. Levanta activando el perfil 'tunnel':
docker compose --profile tunnel up -d

# 3. Verificar que el túnel esté conectado:
docker compose logs -f cloudflared
```
El tráfico público HTTPS llegará a tu máquina y será ruteado internamente hacia el contenedor `api:8000` con `DEBUG=True` y live-reload.

---

### Modo 3: Despliegue Endurecido (Staging / Producción)
Aplica principios de seguridad ofensiva y defensiva (SAST/DevOps):
- La base de datos **no expone ningún puerto al host** (solo accesible dentro de `hm_v2_network`).
- Uvicorn se ejecuta con 4 workers concurrentes.
- El proceso corre bajo el usuario sin privilegios `appuser` (UID 1001).

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## ⚙️ Configuración de Variables de Entorno (.env)

El archivo `.env` gobierna el comportamiento según los principios de las aplicaciones **12-Factor**:

```bash
cp .env.example .env
```

| Variable | Propósito y Recomendación |
| :--- | :--- |
| `PROJECT_NAME` | Nombre identificador del servicio que aparecerá en Swagger UI. |
| `ENVIRONMENT` | `development` (logs detallados) o `production`. |
| `DEBUG` | `True` para desarrollo (muestra trazas en errores) / `False` en prod. |
| `API_V1_STR` | Prefijo unificado de rutas (`/api/v1`). |
| `BACKEND_CORS_ORIGINS` | Lista JSON de URLs permitidas para el Frontend (ej. `["http://localhost:5173"]`). |
| `DATABASE_URL` | URL de conexión a la BD. En Docker: `postgresql://postgres:postgres_password@db:5432/honeymetrics_v2`. En host local: `sqlite:///./honeymetrics_v2.db`. |
| `SECRET_KEY` | Semilla criptográfica para firmar JWT. En producción generar con `openssl rand -hex 32`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de sesión (por defecto 60 minutos). |
| `CLOUDFLARE_TUNNEL_TOKEN` | Token del túnel Zero Trust (dejar vacío si no se usa acceso remoto). |

---

## 💻 Ejecución Alternativa en Host (.venv Local)

Si en clase trabajas en una laptop sin Docker instalado:

```bash
# 1. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Inicializar base de datos SQLite y crear usuarios base
python scripts/seed_admin.py

# 4. Iniciar servidor Uvicorn
uvicorn app.main:app --reload --port 8001
```

---

## 🧪 Poblado de Base de Datos (Seeds) y Pruebas Unitarias

### Ejecutar Seeds (Poblado de Usuarios)
Crea las tablas y los usuarios de prueba institucional:
```bash
# En host local:
python scripts/seed_admin.py

# O dentro del contenedor Docker:
docker compose exec api python scripts/seed_admin.py
```
*Usuarios creados por defecto (contraseña: `Admin123!`):*
- `jsebastianposada@ucundinamarca.edu.co` (Rol: admin)
- `jpablofonseca@ucundinamarca.edu.co` (Rol: admin)
- `admin@honeymetrics.com` (Rol: admin / testing)

### Ejecutar Pruebas Automatizadas con Pytest
Verifica el cumplimiento estricto de los contratos DTO y el Service Layer:
```bash
# En host local:
pytest tests/unit/ -v

# O dentro de Docker:
docker compose exec api pytest tests/unit/ -v
```

---

## 📑 Documentación Interactiva (Swagger / OpenAPI)
Con el servidor en ejecución, accede a la documentación viva autogenerada:
- **Swagger UI (Pruebas interactivas):** [http://localhost:8001/docs](http://localhost:8001/docs)
- **Redoc (Especificación de contratos):** [http://localhost:8001/redoc](http://localhost:8001/redoc)
- **Contrato OpenAPI JSON:** [http://localhost:8001/api/v1/openapi.json](http://localhost:8001/api/v1/openapi.json)

---

## 📚 Biblioteca de Documentación Técnica Avanzada (docs/)

Para profundizar en los protocolos metodológicos, contratos y gobernanza ágil, consulta los documentos especializados:
- 📖 [Índice General de Documentación Técnica](docs/README.md)
- 🤝 [Coordinación de Contratos API y Formato JSON (Frontend ↔ Backend)](docs/arquitectura/contratos-api-y-json.md)
- 📋 [Guía de Puesta en Marcha de Trello y Dailies en Slack](docs/guias/puesta-en-marcha-trello-slack.md)
- 🎓 [Protocolo de Mentoría y Aprendizaje Guiado con IA](docs/metodologia/aprendizaje-guiado-ia.md)
- 🏛️ [Arquitectura de Software y Justificación de Capas](docs/arquitectura.md)
