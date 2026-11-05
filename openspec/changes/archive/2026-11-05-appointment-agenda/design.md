# Design

## Context

El proyecto ya tiene una fundación FastAPI con PostgreSQL, migraciones y
pruebas. La KB define `Box` y `Appointment`, exige aislamiento por
`clinic_id`, persistencia UTC y la regla RN-01 de no solapamiento. C-02 debe
proveer usuarios y contexto de clínica antes de integrar la agenda.

## Goals / Non-Goals

**Goals:**

- Implementar el contrato de [spec.md](specs/appointment-agenda/spec.md) en
  capas separadas de persistencia, servicios y API.
- Hacer que la prevención de solapamientos sea consistente ante concurrencia.
- Cubrir aislamiento, validaciones, estados y límites temporales con pruebas.

**Non-Goals:**

- No implementar autenticación ni RBAC, que pertenecen a C-02.
- No integrar WhatsApp, portal público, pagos ni facturación.
- No convertir horarios en la API; la persistencia y los payloads internos usan
  UTC y la presentación local queda para la interfaz.

## Decisions

1. **Servicio de dominio para solapamientos.** La consulta usará el intervalo
   abierto en el límite (`existing.start < new.end` y
   `existing.end > new.start`), por lo que dos turnos consecutivos son válidos.
   Centralizar la regla evita duplicarla entre endpoints; una validación solo en
   el router sería más fácil de omitir.

2. **Restricción transaccional además de validación previa.** El servicio realiza
   la comprobación previa de intervalos libres y serializa las altas concurrentes
   mediante `appointment_resource_lock` por clínica y recurso (`dentist_id`, `box_id`)
   en memoria, complementado con row-locking (`with_for_update`) y la restricción
   PostgreSQL `EXCLUDE USING gist` en la base de datos (con fallback tolerante en
   SQLite). Si una colisión concurrente supera la validación previa, el repositorio
   captura el conflicto transaccional bajo un savepoint aislado y lo traduce a
   `AppointmentOverlap` (HTTP 409 `appointment_overlap`), garantizando que exactamente
   una cita se persiste sin exponer detalles SQL ni violar la integridad.

3. **Filtrado y derivación por clínica.** Las consultas de boxes, pacientes,
   `dentist_id` y turnos incluirán `clinic_id`; un recurso de otra clínica se
   tratará como inexistente (`404`, misma forma que un ID inexistente). Al
   escribir, el `clinic_id` se deriva **solo** del contexto autenticado y el
   payload que intente enviarlo se rechaza con `422` (ver spec "Agenda clinic
   scope is server-derived"). Esto evita filtraciones aunque el UUID sea válido.

4. **Estados como enum persistido.** Se usará un conjunto cerrado de estados
   alineado con la KB. Cancelar libera el intervalo porque los turnos
   cancelados no participan en el control de solapamiento. La matriz de
   transiciones declarada en la spec solo incluye las que respalda
   `knowledge-base/07_flujos_principales.md` §Flujo 1/2.

5. **Datetimes conscientes normalizados en el borde.** El esquema Pydantic de
   entrada exige un datetime con zona; un naive se rechaza con `422` y un offset
   se convierte a UTC antes de llegar al servicio. Así la capa de persistencia
   nunca recibe ambigüedad horaria (RN-07).

## Open Questions

Requieren decisión del usuario; se documenta la resolución o diferimiento:

1. **[RESUELTO] Implementación de RN-01 portable entre SQLite y PostgreSQL.**
   Se adoptó una estrategia dual de protección:
   - **En aplicación / servicio:** serialización en memoria vía `appointment_resource_lock`
     por clínica y recurso (`dentist_id`, `box_id`), acompañada de `with_for_update` en
     consultas a `users` y `boxes`.
   - **En persistencia / base de datos:** restricción física condicional en PostgreSQL vía
     `EXCLUDE USING gist (clinic_id WITH =, dentist_id/box_id WITH =, tstzrange(start_time, end_time) WITH &&)`
     habilitada mediante la extensión `btree_gist` en Alembic.
   - **Manejo de excepciones:** `AppointmentRepository` aísla las escrituras en savepoints
     anidados (`_isolated_savepoint`) traduciendo cualquier `IntegrityError` a
     `AppointmentOverlap` (HTTP 409 `appointment_overlap`).
   - Verificado con test concurrente `test_concurrent_appointment_booking_rejects_overlap_with_409`
     donde de dos solicitudes paralelas idénticas exactamente una se persiste (201) y la otra
     recibe 409 con código semántico.

2. **Origen de `no_show` [Fuera de alcance C-04].** La KB define el estado pero ningún flujo lo asigna.
   La matriz de la spec no lo incluye; queda diferido a los flujos de atención clínica (C-05/C-10).

3. **Alta de turno sobre un box en `maintenance` [Fuera de alcance C-04].** La KB define el estado del
   box pero no prohíbe agendar en él. C-04 no lo restringe y filtra por `active` al listar boxes;
   reglas de mantenimiento quedan diferidas a administración avanzada.

4. **Titularidad de la auditoría de cancelaciones (RN-04) [Fuera de alcance C-04].** `AuditLog` está
   exigido por RN-04, cuyo flujo corresponde a recordatorios y cancelaciones por WhatsApp (C-06).
   C-04 expone la API de cancelación (`cancelled`) y la persistencia de `AuditLog` queda en C-06.

5. **Filtro de estado por defecto en el listado de turnos [Fuera de alcance C-04].** La spec exige
   filtrado por clínica y rango de fechas con parámetro `status` opcional. El comportamiento
   por defecto retorna todos los estados del rango para el profesional/recepción.

## UI Mockups

- **Decision:** no (no UI)
- **Date:** 2026-11-04
- **Rationale:** C-04 es backend-only (modelos, servicios y endpoints). El
  proyecto no registra un modo de `design-system/` y este change no introduce
  pantallas, componentes ni cambios visuales; la política de mockups no aplica.

## Risks / Trade-offs

- **[Concurrencia — resuelta y verificada]** Dos altas simultáneas para el mismo
  intervalo se serializan mediante `appointment_resource_lock` en memoria y
  `with_for_update`, respaldadas por la restricción PostgreSQL `EXCLUDE USING gist`
  (`btree_gist`). Cualquier colisión transaccional se traduce a `AppointmentOverlap`
  (HTTP 409 `appointment_overlap`) mediante savepoints aislados sin exponer SQL.
  Verificado con prueba concurrente automatizada.
- **[Dependencia C-02 — consumida]** Se integró el contexto real de usuario y
  clínica provisto por `core-models-tenants` (`get_current_principal`,
  `require_roles`, `TenantScopedRepository`) sin recurrir a adaptadores provisionales.
- **[UTC — verificado]** Payloads con datetimes naive son rechazados con 422
  (`validation_error`) y los conscientes son normalizados estrictamente a UTC
  en el límite de entrada por esquemas Pydantic V2 y servicios de dominio (RN-07).
- **[Portabilidad de pruebas — verificado]** La suite completa pasa al 100% (259 tests)
  tanto sobre SQLite como sobre PostgreSQL en contenedor Docker Compose, asegurando
  la portabilidad del servicio y la efectividad de las restricciones.
- **[Preguntas abiertas restantes — fuera de alcance]** Las preguntas 2 a 5
  (origen de `no_show`, boxes en `maintenance`, auditoría `AuditLog` para RN-04,
  y filtro por defecto de turnos cancelados) quedan explícitamente fuera del alcance
  de C-04 y se difieren a sus respectivos changes (C-06, C-10).

## Migration Plan

1. Agregar migración para boxes y appointments (`0005_appointments.py`).
2. Ejecutar migraciones y pruebas sobre la base aislada SQLite y PostgreSQL.
3. Desplegar routers y servicios detrás del contexto multi-tenant de C-02.
4. Revertir la migración y deshabilitar los routers si la verificación falla.
