# ETAPA 1: Build de dependencias
FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir pip==24.3.1 && \
    pip install --no-cache-dir --only-binary :all: --prefix=/install -r requirements.txt

# ETAPA 2: Runtime de Desarrollo y Producción (Seguridad Non-Root)
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar utilidades y librerías C
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario sin privilegios
RUN useradd -m -r -u 1001 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser alembic /app/alembic
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml
COPY --chown=appuser:appuser tests /app/tests

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
