## 🎯 Objetivo de la Pull Request
<!-- Describe en 1 o 2 oraciones qué soluciona o implementa este PR -->

## 📋 Historia de Usuario / Tarea de Scrum Asociada
- **Historia:** `US-XX: [Nombre de la Historia]`
- **Story Points:** `[X] pts`
- **Asignado:** `@JohanPosada` / `@JuanPabloFonseca`

## 🛠️ Cambios Realizados
- [ ] Implementación de DTOs / Schemas correspondientes.
- [ ] Service Layer / Lógica pura de negocio.
- [ ] Controlador liviano (Thin Controller) en `api/v1/endpoints/`.
- [ ] Componentes de UI o actualización de Mocks en Frontend.
- [ ] Pruebas unitarias automatizadas añadidas o actualizadas.

## 🧪 Recibos de Verificación (Receipt-Driven Development)
<!-- Pega aquí la evidencia de que las pruebas pasaron -->
```bash
# Ejemplo:
pytest tests/unit/ -v
# o
npm run build
```

## 🔒 Checklist de Seguridad y Calidad
- [ ] No contiene secretos, tokens o contraseñas en texto plano.
- [ ] Cumple con la regla de arquitectura desacoplada (Cero templates HTML en Django/FastAPI).
- [ ] Los endpoints cumplen con las convenciones REST y retorno tipado de DTOs.
- [ ] Historial de Git atómico (sin commits masivos `git add .`).
