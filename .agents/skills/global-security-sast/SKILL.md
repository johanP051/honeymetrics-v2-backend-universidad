---
name: global-security-sast
description: >-
  Estándar global de Seguridad de Aplicaciones (AppSec), auditoría estática SAST,
  mitigación de OWASP Top 10 2021, protección de endpoints, JWT, CORS y prevención de fugas de datos.
---

# 🛡️ Global AppSec & SAST Security Standard

Esta Skill aplica a **todos** los proyectos de desarrollo para garantizar estándares de ciberseguridad desde el diseño (Security-by-Design).

## 1. Reglas Críticas OWASP Top 10 (2021)
- **A01: Broken Access Control:** Verificar autenticación y autorización en cada endpoint. Prohibido confiar en IDs enviados por el cliente sin verificar pertenencia (IDOR).
- **A02: Cryptographic Failures:** Hashes seguros de contraseñas (Argon2, bcrypt o PBKDF2). Tokens JWT firmados con algoritmos seguros y secretos robustos.
- **A03: Injection:** Consultas SQL siempre parametrizadas a través de ORM o queries preparadas. Cero concatenación de strings en SQL o comandos del sistema.
- **A05: Security Misconfiguration:**
  - `DEBUG=False` obligatorio en entornos productivos.
  - CORS configurado con orígenes explícitos (nunca `allow_origins=["*"]` con credenciales activadas).
- **A07: Identification & Auth:** Rate limiting en rutas de login y recuperación. Expiración estricta de tokens de acceso (Access Tokens de corta duración + Refresh Tokens).

## 2. Checklist de Auditoría Pre-Commit
- [ ] No hay claves secretas ni tokens en archivos versionados (`.git`).
- [ ] `.env` está incluido en `.gitignore`.
- [ ] CORS no expone métodos inseguros a dominios desconocidos.
- [ ] Los errores devueltos al cliente no filtran trazas internas (*stack traces*) ni detalles de la infraestructura.
