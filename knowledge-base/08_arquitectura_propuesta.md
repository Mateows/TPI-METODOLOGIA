# 08. Arquitectura Propuesta — TPI Metodologia

## 1. Patrones de Diseño
- **Clean Architecture / Layered Architecture en Backend:** Separación en Routers (Endpoints HTTP), Services (Lógica de Negocio), Models/Repositories (Acceso a Datos SQLAlchemy).
- **Component-Driven Development en Frontend:** Componentes reutilizables con React, Tailwind CSS y Context API para autenticación y estado global.

## 2. Estructura de Directorios Propuesta
```text
tpi-metodologia/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers FastAPI (v1)
│   │   ├── core/         # Config, seguridad, base de datos
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Modelos Pydantic (DTOs)
│   │   ├── services/     # Lógica de negocio
│   │   └── main.py       # Punto de entrada FastAPI
│   ├── alembic/          # Migraciones de base de datos
│   └── tests/            # Tests unitarios e integración (pytest)
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Vistas por rol (Agenda, Pacientes, Caja)
│   │   ├── services/     # Clientes API (Axios)
│   │   └── App.tsx
│   └── package.json
└── docker-compose.yml
```

## 3. Seguridad y Variables de Entorno
- Autenticación mediante **JWT (JSON Web Tokens)** con expiración y refresh tokens.
- Cifrado de contraseñas con **Bcrypt**.
- Variables de entorno estrictas (`.env`): `DATABASE_URL`, `SECRET_KEY`, `WHATSAPP_API_TOKEN`, `AFIP_CERT_PATH`, `AFIP_CUIT`.

## 4. Requisitos Transversales (D-2)
- **Cifrado en reposo (exigido por RN-02):** datos de historias clínicas, diagnósticos e imágenes cifrados en reposo + segregación estricta por `clinic_id` (Ley 25.326).
- **UTC:** persistencia en UTC; conversión a `America/Argentina/Buenos_Aires` solo en UI (RN-07).
- **Idempotencia:** `idempotency_key` UNIQUE en `Payment` + manejo de reintentos para Mercado Pago y llamadas críticas AFIP (RN-06).
- **Estrategia de tests mínima (coherente con C-01):** `pytest` + fixtures para unitarios e integración; los tests viven en `backend/tests/`.
