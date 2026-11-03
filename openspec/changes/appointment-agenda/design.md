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
   solicitudes concurrentes, usando el mecanismo compatible con PostgreSQL.
   Solo consultar antes de insertar no alcanza para evitar carreras.

3. **Filtrado por clínica en cada operación.** Las consultas de boxes,
   pacientes, profesionales y turnos incluirán `clinic_id`; un recurso de otra
   clínica se tratará como inexistente. Esto evita filtraciones aunque el UUID
   sea válido.

4. **Estados como enum persistido.** Se usará un conjunto cerrado de estados
   alineado con la KB. Cancelar libera el intervalo porque los turnos
   cancelados no participan en el control de solapamiento.

## Risks / Trade-offs

- **[Concurrencia]** Dos altas simultáneas podrían competir por el mismo
  intervalo -> usar aislamiento/restricción de PostgreSQL y traducir la
  violación a conflicto HTTP, sin exponer detalles SQL.
- **[Dependencia C-02 — resuelta el 2026-11-02]** El contexto real de usuario y
  clínica ya existe en `core-models-tenants` (`get_current_principal`,
  `require_roles`, `TenantScopedRepository`): al implementar C-04 se consume ese
  contexto en lugar de los adaptadores provisionales. C-04 sigue sin
  implementar.
- **[UTC]** Payloads con offsets ambiguos pueden producir errores de agenda ->
  validar datetimes conscientes y normalizarlos a UTC en el límite de entrada.

## Migration Plan

1. Agregar migración para boxes y appointments.
2. Ejecutar migraciones y pruebas sobre la base aislada.
3. Desplegar routers y servicios detrás del contexto multi-tenant de C-02.
4. Revertir la migración y deshabilitar los routers si la verificación falla.
