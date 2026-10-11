# 05. Reglas de Negocio — TPI Metodologia

- **RN-01: Prevención de Solapamiento de Turnos**
  - El sistema no debe permitir agendar un turno para un mismo profesional (`dentist_id`) o un mismo box (`box_id`) si existe solapamiento de horario (`start_time` - `end_time`). La duración se deriva como `end_time − start_time`; el alta exige `end_time > start_time`.

- **RN-02: Protección de Datos Sensibles de Salud (Ley 25.326)**
  - Todos los datos de historias clínicas, diagnósticos e imágenes de pacientes deben almacenarse con cifrado en reposo y acceso estrictamente segregado por `clinic_id`. Ningún usuario externo o de otra clínica puede acceder sin autorización explícita.

- **RN-03: Validación Fiscal AFIP/ARCA**
  - Toda factura emitida debe validar el CUIT/DNI del receptor y conectarse con los servicios web de AFIP para la obtención del CAE antes de registrar el cobro definitivo en caja.

- **RN-04: Confirmación y Cancelación de Turnos por WhatsApp**
  - Los turnos que reciban confirmación negativa (botón "Cancelar" en WhatsApp) deben liberar automáticamente el slot de agenda y cambiar su estado a `cancelled`, registrando el evento en el log de auditoría.

- **RN-05: Integridad de Caja Diaria**
  - Ninguna caja diaria puede cerrarse si existen transacciones pendientes de conciliar con medios de pago digitales o efectivo declarado.

- **RN-06: Idempotencia en Pagos y Facturación**
  - Toda operación con Mercado Pago y toda llamada crítica a AFIP/ARCA debe enviar una clave de idempotencia (`idempotency_key` UNIQUE en `Payment`). Ante reintento con la misma clave, el sistema retorna el resultado original sin duplicar cobros ni comprobantes.

- **RN-07: Consistencia Temporal (UTC)**
  - Todas las fechas y horas se persisten en UTC en base de datos. La conversión a hora local de Argentina (`America/Argentina/Buenos_Aires`) se realiza únicamente en la capa de interfaz.

- **RN-08: Presupuesto genera Cuenta Corriente**
  - Todo presupuesto aceptado (`Budget` en estado `accepted`/`billed`, con `clinic_id` + `patient_id`) debe generar ítems de cargo (`AccountEntry` con `entry_type=charge`) en la cuenta corriente del paciente. Sin firma digital en MVP (firma digital → V1.5).

- **RN-09: Comisiones y Liquidación de Honorarios → V2**
  - La liquidación automática de honorarios/comisiones de profesionales queda fuera del MVP (V2 con alcance explícito). En V1 solo se exponen como métrica de visibilidad financiera, sin motor de liquidación automática.
