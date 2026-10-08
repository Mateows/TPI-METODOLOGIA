# 02. Descripción General — TPI Metodologia

## 1. Stack Tecnológico
- **Backend:** Python 3.11+ con **FastAPI** (API REST asincrónica, tipado estricto con Pydantic).
- **Frontend:** React 18+ con TypeScript, Tailwind CSS (interfaz SPA responsiva).
- **Base de Datos & ORM:** PostgreSQL con SQLAlchemy y Alembic para migraciones.
- **Contenerización & Despliegue:** Docker y Docker Compose para desarrollo y despliegue estandarizado en la nube (ej. Railway, Render o AWS).
- **Control de Versiones:** Git / GitHub.

## 2. Arquitectura General
El sistema adopta una arquitectura de **Servicios Modulares en FastAPI** combinada con una SPA en React. 
- **Aislamiento Multi-Tenant:** Cada clínica u odontólogo independiente opera en su propio espacio lógico segregado mediante `clinic_id` en todas las consultas transaccionales, garantizando privacidad estricta conforme a la Ley 25.326.
- **Capa de Servicios:** Separación clara entre enrutadores HTTP, lógica de negocio (servicios) y persistencia (repositorios).

## 3. Integraciones Externas Clave
- **WhatsApp Business API:** Envío de recordatorios, confirmaciones y enlaces de autogestión de turnos.
- **Mercado Pago API:** Procesamiento de pagos y señas de turnos online.
- **AFIP / ARCA (Web Services de Facturación Electrónica):** Emisión directa de comprobantes fiscales (Factura C / B) en Argentina.
- **Google Calendar (Opcional):** Sincronización de agenda profesional.
