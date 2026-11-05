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

2. **Restricción transaccional además de validación previa.** El servicio hará
   la comprobación legible y la transacción protegerá la escritura frente a
   solicitudes concurrentes. Solo consultar antes de insertar no alcanza para
   evitar carreras. El mecanismo concreto está **pendiente de decisión del
   usuario** (ver Open Questions → RN-01 y portabilidad SQLite/PostgreSQL); este
   documento no lo da por elegido.

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

Requieren decisión del usuario; no se resuelven en este change.

1. **Implementación de RN-01 portable entre SQLite y PostgreSQL.** La suite se
   ejecuta sobre ambas bases. Opciones conocidas:
   - **(a) Chequeo en el servicio con bloqueo/advisory lock portátil:** el
     servicio valida el intervalo y serializa el alta por `clinic_id` +
     recurso. Portable, sin guardas por dialecto; el costo es que la garantía
     depende de que toda escritura pase por el servicio y de un lock
     correctamente implementado.
   - **(b) `EXCLUDE USING gist (tstzrange(start_time, end_time) WITH &&)` +
     `btree_gist`:** invariante en la base, imposible de saltear; requiere
     PostgreSQL y una guarda por dialecto en la migración
     (`op.get_bind().dialect.name`), dejando SQLite sin la restricción y con el
     chequeo del servicio como red de contención. Consecuencia sobre el harness:
     las pruebas de concurrencia solo serían significativas en PostgreSQL.
   - **Consecuencia de no decidir:** la tarea 1.2 (integridad en la migración) y
     la 2.4 (criterio de concurrencia) no pueden cerrarse con un criterio
     verificable.

2. **Origen de `no_show`.** La KB define el estado pero ningún flujo lo asigna.
   La matriz de la spec no lo incluye; cualquier transición hacia `no_show` debe
   decidirse antes de implementar.

3. **Alta de turno sobre un box en `maintenance`.** La KB define el estado del
   box pero no prohíbe agendar en él. C-04 no lo restringe hasta que se decida;
   hoy solo se filtra por `active` al listar (ver tarea 2.1).

4. **Titularidad de la auditoría de cancelaciones (RN-04).** `AuditLog` está
   exigido por RN-04, cuyo flujo es WhatsApp (C-06). Debe decidirse si C-04
   emite el registro al cancelar o si esa responsabilidad queda íntegramente en
   C-06. Hasta entonces C-04 no crea `AuditLog`.

5. **Filtro de estado por defecto en el listado de turnos.** La spec exige
   filtrado por clínica y rango de fechas; no define si el listado incluye
   turnos `cancelled` por defecto.

## UI Mockups

- **Decision:** no (no UI)
- **Date:** 2026-11-04
- **Rationale:** C-04 es backend-only (modelos, servicios y endpoints). El
  proyecto no registra un modo de `design-system/` y este change no introduce
  pantallas, componentes ni cambios visuales; la política de mockups no aplica.

## Risks / Trade-offs

- **[Concurrencia]** Dos altas simultáneas podrían competir por el mismo
  intervalo -> el mecanismo definitivo está en Open Questions (1); la violación
  debe traducirse a conflicto HTTP sin exponer detalles SQL.
- **[Dependencia C-02 — resuelta el 2026-11-02]** El contexto real de usuario y
  clínica ya existe en `core-models-tenants` (`get_current_principal`,
  `require_roles`, `TenantScopedRepository`): al implementar C-04 se consume ese
  contexto en lugar de los adaptadores provisionales. C-04 sigue sin
  implementar.
- **[UTC]** Payloads con offsets ambiguos pueden producir errores de agenda ->
  validar datetimes conscientes y normalizarlos a UTC en el límite de entrada
  (requisito y escenarios en la spec, no solo en este diseño).
- **[Portabilidad de pruebas]** Verificar RN-01 solo en SQLite no prueba la
  garantía concurrente de PostgreSQL, y viceversa; depende de la decisión de
  Open Questions (1).

## Migration Plan

1. Agregar migración para boxes y appointments.
2. Ejecutar migraciones y pruebas sobre la base aislada.
3. Desplegar routers y servicios detrás del contexto multi-tenant de C-02.
4. Revertir la migración y deshabilitar los routers si la verificación falla.
