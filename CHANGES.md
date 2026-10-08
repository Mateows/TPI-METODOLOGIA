# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto TPI Metodologia (SaaS Odontológico).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. **Identificar el change actual** en la secuencia o fases.
2. **Leer la KB** indicada en "Leer antes" para cada change.
3. **Proponer el change** con OpenSpec (`/opsx:propose C-NN-nombre`).
4. **Implementar y archivar** (`/opsx:apply` y `/opsx:archive`).
5. **Marcar como completado** `[x]` en este archivo.

---

## Árbol de dependencias

```text
C-01 (Foundation Setup)
└── C-02 (Core Models & Tenants / Auth)
    ├── C-03 (Patient Management)
    │   └── C-05 (Odontogram & Clinical Records) ──┐
    └── C-04 (Appointment Agenda & Boxes)           │
        ├── C-06 (WhatsApp Reminders & API)        │
        ├── C-07 (Cash Register & Payments)       │
        │   └── C-08 (AFIP Electronic Billing) ────┼── C-10 (Admin Dashboard Frontend)
        └── C-09 (Public Booking Portal) ──────────┘
```

### Paralelismo por fase

- **GATE 0**: C-01 ✓
  → C-02 (Core Models & Tenants) [Agente Backend Core]
- **GATE 1**: C-02 ✓     *(PRIMER FORK)*
  → C-03 (Patient Management) [Agente Backend Aux]
  → C-04 (Appointment Agenda) [Agente Backend Core]
- **GATE 2**: C-03 ✓ & C-04 ✓
  → C-05 (Odontogram & Clinical Records) [Agente Backend Core — si C-03 ✓]
  → C-06 (WhatsApp Reminders) [Agente Backend Aux — si C-04 ✓]
  → C-07 (Cash Register & Payments) [Agente Backend Aux — si C-04 ✓]
- **GATE 3**: C-07 ✓
  → C-08 (AFIP Electronic Billing) [Agente Backend Core — si C-07 ✓]
  → C-09 (Public Booking Portal) [Agente Frontend/Backend — si C-04 ✓]
- **GATE 4**: C-05 ✓ & C-08 ✓ & C-09 ✓
  → C-10 (Admin Dashboard Frontend SPA) [Agente Frontend]

### Camino crítico (6 changes — mínimo irreducible)
`C-01` → `C-02` → `C-04` → `C-07` → `C-08` → `C-10`

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux) | Agente C (Frontend / Fullstack) |
|---|---|---|---|
| 1 | C-01 (Foundation Setup) | — | — |
| 2 | C-02 (Core Models & Auth) | — | — |
| 3 | C-04 (Appointment Agenda) | C-03 (Patient Management) | — |
| 4 | C-05 (Odontogram & Clinical) | C-06 (WhatsApp Reminders) | C-07 (Cash Register & Payments) |
| 5 | C-08 (AFIP Electronic Billing) | — | C-09 (Public Booking Portal) |
| 6 | — | — | C-10 (Admin Dashboard SPA) |

---

## FASE 1 — Fundación y Núcleo de Autenticación

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Estructuración del proyecto FastAPI y configuración de Docker Compose (PostgreSQL).
  - Configuración de SQLAlchemy, Alembic para migraciones y Pydantic Settings (`.env`).
  - Configuración de pytest y fixtures base para pruebas de integración.
- **Dependencias**: ninguna
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §1, §2
  - `knowledge-base/08_arquitectura_propuesta.md` §2, §3

### [C-02] `core-models-tenants`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelos SQLAlchemy para `Clinic` y `User` con segregación multi-tenant por `clinic_id`.
  - Sistema de autenticación JWT (Access Token + Refresh Token) y encriptación Bcrypt.
  - Middleware de contexto multi-tenant y verificación de roles RBAC (admin, receptionist, dentist).
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §2, §3
  - `knowledge-base/04_modelo_de_datos.md` §1 (Clinic, User)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-02

---

## FASE 2 — Gestión Clínica y Agenda

### [C-03] `patient-management`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelo SQLAlchemy para `Patient` con campos personales y anamnesis médica en JSON.
  - Endpoints REST CRUD para pacientes (`POST /api/v1/patients`, `GET /api/v1/patients/{id}`, etc.) con filtro por `clinic_id`.
  - Tests unitarios y de aislamiento multi-tenant con pytest.
- **Dependencias**: `C-02`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §1 (Patient)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-02

### [C-04] `appointment-agenda`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelos SQLAlchemy para `Box` y `Appointment` (Turnos).
  - Implementación de regla de negocio **RN-01** (prevención de solapamiento de turnos por profesional y box).
  - Endpoints REST para gestión de agenda, cambios de estado (`scheduled`, `confirmed`, `attended`, `cancelled`).
- **Dependencias**: `C-02`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §1 (Box, Appointment)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01
  - `knowledge-base/07_flujos_principales.md` §Flujo 1

### [C-05] `odontogram-clinical-records`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelos SQLAlchemy para `Odontogram` (nomenclatura ISO 3950 por cara dentaria) y `MedicalRecord` (Evoluciones).
  - Endpoints REST para registrar y consultar diagnósticos y tratamientos por pieza dental.
  - Vinculación automática entre evolución clínica y cuenta corriente del paciente.
- **Dependencias**: `C-03`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §1 (Odontogram, MedicalRecord)
  - `knowledge-base/06_funcionalidades.md` §Épica 2
  - `knowledge-base/07_flujos_principales.md` §Flujo 2

---

## FASE 3 — Integraciones y Facturación

### [C-06] `whatsapp-reminders`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Servicio de integración con WhatsApp Business API para envío de recordatorios automáticos (24h/2h antes).
  - Endpoints Webhook para procesar confirmaciones o cancelaciones interactivas (regla de negocio **RN-04**).
- **Dependencias**: `C-04`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §3
  - `knowledge-base/05_reglas_de_negocio.md` §RN-04
  - `knowledge-base/07_flujos_principales.md` §Flujo 1

### [C-07] `cash-register-payments`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelo de transacciones de caja diaria y medios de pago (efectivo, transferencia, Mercado Pago).
  - Implementación de regla de negocio **RN-05** (integridad y cierre de caja).
  - Endpoints REST para registro de cobros e ingresos diarios.
- **Dependencias**: `C-04`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-05
  - `knowledge-base/06_funcionalidades.md` §Épica 3
  - `knowledge-base/07_flujos_principales.md` §Flujo 3

### [C-08] `afip-billing`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Modelo SQLAlchemy para `Invoice` y servicio conector con Web Services de AFIP/ARCA (Factura C y B).
  - Implementación de regla de negocio **RN-03** (obtención de CAE previo al cierre de cobro).
  - Endpoints REST para emisión de comprobantes fiscales electrónicos.
- **Dependencias**: `C-07`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §3
  - `knowledge-base/04_modelo_de_datos.md` §1 (Invoice)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-03
  - `knowledge-base/07_flujos_principales.md` §Flujo 3

---

## FASE 4 — Portal Web y Panel Frontend

### [C-09] `public-booking-portal`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Aplicación SPA en React para el portal público de turnos (`/portal/reserva/{slug}`).
  - Flujo de selección de profesional, horario disponible, datos de paciente y confirmación online.
- **Dependencias**: `C-04`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 1
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §1

### [C-10] `admin-dashboard-frontend`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Panel administrativo en React (Tailwind CSS) para recepcionistas, odontólogos y administradores.
  - Vistas de agenda interactiva, gestión de pacientes, odontograma visual, caja diaria y emisión de facturas.
- **Dependencias**: `C-05`, `C-08`, `C-09`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §2
  - `knowledge-base/06_funcionalidades.md` §Épica 1, 2, 3, 4
  - `knowledge-base/08_arquitectura_propuesta.md` §1, §2
