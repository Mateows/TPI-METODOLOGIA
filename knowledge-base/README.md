# Base de Conocimiento — TPI Metodologia

Documentación canónica del SaaS odontológico (turnos, HCE, caja, AFIP). Fuente de verdad para proponer e implementar changes. No editar la numeración 01–10 (la exige `kb-creator`).

## Archivos Canónicos

- [01. Visión y Objetivos](01_vision_y_objetivos.md) — para qué existe el producto, MVP (imprescindible/V1.5/V2) y alcance.
- [02. Descripción General](02_descripcion_general.md) — stack (FastAPI+React+PostgreSQL), módulos e integraciones (WhatsApp, Mercado Pago, AFIP).
- [03. Actores y Roles](03_actores_y_roles.md) — odontólogo, recepcionista, administrador, paciente; matriz RBAC y rutas por rol.
- [04. Modelo de Datos](04_modelo_de_datos.md) — entidades (Clinic, User, Patient, Box, Appointment, Payment, Budget, AuditLog) y aislamiento por `clinic_id`.
- [05. Reglas de Negocio](05_reglas_de_negocio.md) — RN-01 (anti-solapamiento) a RN-09 (comisiones V2); contrato verificable de cada change.
- [06. Funcionalidades](06_funcionalidades.md) — épicas F-01–F-09 y su cobertura por change.
- [07. Flujos Principales](07_flujos_principales.md) — reserva/cancelación, presupuesto→cuenta corriente, cobro→CAE paso a paso.
- [08. Arquitectura Propuesta](08_arquitectura_propuesta.md) — Clean Architecture (api/services/models), async, UTC, idempotencia, tests.
- [09. Decisiones y Supuestos](09_decisiones_y_supuestos.md) — ADRs (FastAPI, `clinic_id` lógico, AFIP modular) y supuestos.
- [10. Preguntas Abiertas](10_preguntas_abiertas.md) — lo no resuelto (P-01..P-04 cerradas con su decisión); leer antes de asumir.

## Guía de ruteo para agentes

- Voy a **proponer un change** → 01 (alcance/MVP) + 06 (épica) + `CHANGES.md` (dependencias y "Leer antes").
- Voy a **implementar turnos/agenda** → 04 (Appointment, Box) + 05 (RN-01) + 07 (flujo reserva).
- Voy a **implementar auth/usuarios** → 03 (roles) + 04 (User, Clinic) + 09 (ADR auth).
- Voy a **implementar caja/facturación** → 04 (Payment, Invoice, Budget) + 05 (RN-03, RN-06, RN-08) + 07 (flujo cobro→CAE).
- Hay **duda de diseño** → 09 primero; si sigue abierta, 10 (y se registra, no se inventa).
- Detalle de mercado/competidores → `docs/discovery/informe-discovery.md` (la KB no duplica al Discovery).
