# 07. Flujos Principales — TPI Metodologia

## Flujo 1: Reserva Online y Confirmación por WhatsApp
1. **Paso 1:** El paciente accede al enlace público del consultorio (`/portal/reserva/{slug}`).
2. **Paso 2:** Selecciona la especialidad, el profesional y el horario disponible en la agenda.
3. **Paso 3:** Completa sus datos personales (DNI, nombre, teléfono, email).
4. **Paso 4:** El sistema valida que no exista solapamiento (RN-01), crea el turno en estado `scheduled` y envía un mensaje de confirmación vía WhatsApp API.
5. **Paso 5:** 24 horas antes, el sistema envía un recordatorio por WhatsApp con botones "Confirmar" / "Cancelar".
6. **Paso 6:** Si el paciente confirma, el turno pasa a `confirmed`. Si cancela, pasa a `cancelled` y se libera el slot.

## Flujo 2: Atención Clínica y Odontograma
1. **Paso 1:** El paciente llega a la clínica y la recepcionista marca el turno como `attended`.
2. **Paso 2:** El odontólogo abre la ficha del paciente desde su dashboard.
3. **Paso 3:** Selecciona el odontograma interactivo, hace clic en la pieza y cara afectada, y registra el diagnóstico o tratamiento realizado.
4. **Paso 4:** Guarda la evolución clínica; el sistema genera automáticamente el ítem pendiente en la cuenta corriente del paciente.

## Flujo 3: Cobro y Facturación AFIP
1. **Paso 1:** Al finalizar la consulta, el paciente pasa por recepción.
2. **Paso 2:** La recepcionista selecciona los ítems pendientes a cobrar y elige el método de pago (ej. Mercado Pago / Efectivo).
3. **Paso 3:** Se procesa el pago y se solicita la emisión de factura electrónica a AFIP/ARCA (RN-03).
4. **Paso 4:** Se genera el CAE, se imprime o envía por email el comprobante fiscal y se registra el ingreso en la caja diaria (RN-05).
