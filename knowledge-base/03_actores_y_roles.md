# 03. Actores y Roles — TPI METODOLOGIA

## 1. Definición de Actores
1. **Odontólogo:** Profesional matriculado que realiza diagnósticos, evoluciones clínicas, tratamientos y recetas.
2. **Recepcionista:** Personal administrativo encargado de la gestión de turnos, sala de espera, cobros diarios y atención al público.
3. **Administrador / Director:** Dueño de la clínica o gerente con privilegios de configuración general, gestión de profesionales, reportes financieros y liquidaciones.
4. **Paciente:** Usuario final que interactúa mediante el portal público para agendar turnos y ver su historial/presupuestos.

## 2. Matriz de Control de Acceso (RBAC)

| Recurso / Módulo | Odontólogo | Recepcionista | Administrador | Paciente |
|------------------|------------|---------------|---------------|----------|
| **Agenda General** | Propia / Read-only | Lectura / Escritura total | Lectura / Escritura total | Solo propios (vía portal) |
| **Historia Clínica** | Lectura / Escritura total | Sin acceso | Lectura (auditoría) | Solo propia (resumen) |
| **Odontograma** | Lectura / Escritura total | Sin acceso | Sin acceso | Solo visualización |
| **Caja y Pagos** | Sin acceso | Lectura / Escritura diaria | Control total de caja y cierres | Solo comprobantes propios |
| **Facturación AFIP** | Sin acceso | Emisión básica | Configuración y emisión total | Descarga de factura propia |
| **Configuración Clínica**| Sin acceso | Sin acceso | Control total | Sin acceso |

## 3. Rutas Públicas y Privadas
- **Rutas Públicas:** `/login`, `/portal/reserva/{clinic_slug}`, `/api/v1/webhook/whatsapp`.
- **Rutas Privadas (requieren autenticación JWT y rol autorizado):** `/dashboard/*`, `/agenda/*`, `/pacientes/*`, `/caja/*`, `/config/*`.
