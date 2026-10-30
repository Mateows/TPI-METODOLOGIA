# Proposal

## Why

La agenda es el siguiente change habilitado del roadmap y necesita una regla
verificable para evitar dobles reservas por profesional o por box. Preparar esta
capacidad ahora permite validar los escenarios de agenda antes de implementar
los endpoints y reduce el riesgo de inconsistencias en los turnos.

## What Changes

- Agregar modelos para boxes y turnos, vinculados estrictamente a `clinic_id`.
- Definir la creación, consulta y cambio de estado de turnos mediante servicios y
  endpoints FastAPI.
- Rechazar rangos inválidos y solapamientos por profesional o box.
- Persistir fechas en UTC y mantener errores de negocio explícitos.
- Mantener fuera de alcance la implementación de WhatsApp, portal público,
  recordatorios, pagos y facturación.

## Capabilities

### New Capabilities

- `appointment-agenda`: Gestión de boxes y turnos con aislamiento por clínica,
  estados y prevención de solapamientos.

### Modified Capabilities

- Ninguna.

## Impact

- Backend: `models/`, `services/`, `api/`, migraciones y pruebas de agenda.
- Documentación: referencia del change en `CHANGES.md` y KB relacionada.
- La implementación dependerá de C-02 para usuarios/profesionales y contexto
  multi-tenant; este documento no implementa ni marca esa dependencia como
  completada.
