# Tasks

## 1. Modelo y migración

- [x] 1.1 Agregar modelos tipados `Box` y `Appointment` con `clinic_id`,
  referencias (`patient_id`, `dentist_id`, `box_id`), estados e índices;
  verificar con tests de esquema que las columnas y relaciones esperadas
  existen.
- [x] 1.2 Crear la migración PostgreSQL para boxes y turnos (`0005_appointments.py`),
  incluyendo la estrategia de integridad para evitar solapamientos (RN-01) con
  restricción condicional `EXCLUDE USING gist` y `btree_gist` bajo guarda de dialecto
  PostgreSQL, manteniendo SQLite operativo; verificar aplicando la migración e idempotencia.
- [x] 1.3 Documentar en el módulo de persistencia las invariantes UTC y de
  aislamiento; verificar que la documentación coincide con la migración y la
  KB.

## 2. Servicio de agenda

- [x] 2.1 Implementar creación y consulta de boxes filtradas por `clinic_id`
  (incluyendo endpoint individual `GET /api/v1/boxes/{id}`), derivando el
  `clinic_id` persistido del contexto autenticado y rechazando con `422` todo payload
  que envíe `clinic_id`; verificar con una prueba de alta válida, una de payload con
  `clinic_id` rechazado y una de UUID de otra clínica que responde `404` sin revelar datos.
  No restringir el alta de turnos por estado del box; la regla de mantenimiento queda
  fuera de alcance de C-04 (diferida en `design.md` §Open Questions 3).
- [x] 2.2 Implementar creación de turnos con referencias de la misma clínica,
  datetimes obligatoriamente conscientes normalizados a UTC y
  `end_time > start_time`; verificar escenarios válido, rango inválido,
  datetime naive rechazado con `422` y offset `-03:00` persistido como el
  instante UTC equivalente.
- [x] 2.3 Implementar detección de solapamiento por `dentist_id` **o** `box_id`
  con límites consecutivos permitidos y exclusión de turnos `cancelled`;
  verificar, al menos: (a) solapamiento parcial por `dentist_id` rechazado;
  (b) solapamiento por `box_id` rechazado aunque el `dentist_id` difiera;
  (c) cita contenida dentro de otra rechazada; (d) coincidencia exacta de
  `start_time`/`end_time` rechazada; (e) turnos consecutivos (`end == start`)
  aceptados; (f) turno `cancelled` en el mismo intervalo no bloquea el alta.
- [x] 2.4 Traducir conflictos de concurrencia y reglas de negocio a errores
  semánticos sin exponer trazas SQL mediante savepoints aislados (`_isolated_savepoint`);
  verificar con la prueba concurrente implementada (`test_concurrent_appointment_booking_rejects_overlap_with_409`)
  que dos altas concurrentes del mismo intervalo serializan mediante `appointment_resource_lock`
  y dejan exactamente una persistida (201) y la otra recibe `409 appointment_overlap`.
- [x] 2.5 Implementar la matriz de transiciones de la spec
  (`scheduled→confirmed`, `scheduled→cancelled`, `confirmed→attended`,
  `confirmed→cancelled`) y su aislamiento por clínica; verificar confirmación
  válida, transición no declarada rechazada con el estado previo preservado y
  estado desconocido rechazado. C-04 no crea `AuditLog`; la auditoría de
  cancelaciones por WhatsApp (RN-04) queda fuera de alcance y diferida a C-06.

## 3. API y documentación

- [x] 3.1 Exponer endpoints FastAPI para boxes (alta, listado y lectura individual `GET /{id}`),
  alta y consulta/listado de turnos usando los servicios, esquemas Pydantic estrictos (sin campo
  `clinic_id` de entrada) y el contexto multi-tenant de C-02; verificar
  payloads válidos, errores 4xx, listado filtrado por clínica y rango de fechas,
  lectura cross-clinic que responde `404` y ausencia de `any` en contratos
  TypeScript si se agrega cliente.
- [x] 3.2 Actualizar la documentación de API y el flujo de agenda con los
  estados, códigos de error y formato UTC; verificar que los ejemplos sean
  reproducibles sin datos reales.
- [x] 3.3 Agregar pruebas de integración de los tres escenarios obligatorios
  (funcionamiento, error de negocio y borde) contra la base aislada; verificar
  que la suite dirigida pase sin escribir en la base de desarrollo y que las
  pruebas de aislamiento corran contra el contexto real de C-02, no contra un
  stub.

## 4. Integración

- [x] 4.1 Ejecutar validación OpenSpec y revisión de reglas contra la KB;
  verificar que todos los requisitos tengan escenarios y que no se marque el
  change como implementado antes de completar las pruebas.

## Workflow follow-up

- C-02 (`core-models-tenants`) está archivado y disponible desde el 2026-11-02
  (`get_current_principal`, `require_roles`, `TenantScopedRepository`).
- Tareas implementadas usando el contexto real multi-tenant de C-02, sin adaptadores
  provisionales.
- Decisión de concurrencia de RN-01 resuelta e implementada en 1.2 y 2.4; preguntas
  restantes fuera de alcance diferidas formalmente a C-06 y C-10.
- Ejecutar la validación completa del change y archivarlo únicamente después
  de una implementación verificada.
