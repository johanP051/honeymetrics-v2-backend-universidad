# Arquitectura de Software — HoneyMetrics Backend

## 1. Justificación del Patrón N-Capas
El desacoplamiento de capas permite:
- **Testabilidad Aislada:** Las capas de servicio (`services/`) y esquemas (`schemas/`) se pueden probar con Pytest en milisegundos sin levantar conexiones HTTP ni servidores web.
- **Sustituibilidad de Infraestructura:** Si se migra el motor de base de datos de PostgreSQL a MariaDB o SQLite para pruebas en memoria, la capa de Controladores y Servicios no sufre ningún cambio.
- **Cumplimiento de Principios SOLID:** Especialmente el principio de Responsabilidad Única (SRP) y de Inversión de Dependencias (DIP).

## 2. Convenciones de Código (PEP-8)
- Nombres de archivos en minúsculas con guiones bajos (`snake_case`).
- Controladores en `app/api/v1/endpoints/*.py` con funciones asíncronas (`async def`).
- Modelos DTO en `app/schemas/*.py` heredando de `pydantic.BaseModel`.
- Servicios en `app/services/*_service.py` como clases con métodos de clase o estáticos puros.
