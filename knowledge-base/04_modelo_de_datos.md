# 04. Modelo de Datos — TPI Metodologia

## 1. Entidades Principales y Relaciones (ERD Conceptual)

- **Clinic (Clínica / Consultorio):**
  - `id` (PK, UUID)
  - `name`, `tax_id` (CUIT), `address`, `phone`, `settings` (JSON)
  - *Relación:* 1:N con `User`, `Patient`, `Box`, `Appointment`.

- **User (Usuario del Sistema):**
  - `id` (PK, UUID), `clinic_id` (FK)
  - `email`, `password_hash`, `full_name`, `role` (admin, receptionist, dentist), `is_active`

- **Patient (Paciente):**
  - `id` (PK, UUID), `clinic_id` (FK)
  - `first_name`, `last_name`, `dni`, `email`, `phone`, `birth_date`, `medical_history_summary` (JSON)
  - *Relación:* 1:N con `Appointment`, `MedicalRecord`, `Odontogram`, `Invoice`.

- **Box (Box / Sillón Odontológico):**
  - `id` (PK, UUID), `clinic_id` (FK)
  - `name`, `status` (active, maintenance)

- **Appointment (Turno):**
  - `id` (PK, UUID), `clinic_id` (FK), `patient_id` (FK), `dentist_id` (FK), `box_id` (FK)
  - `start_time`, `end_time`, `status` (scheduled, confirmed, attended, cancelled, no_show), `notes`

- **MedicalRecord (Evolución Clínica):**
  - `id` (PK, UUID), `patient_id` (FK), `dentist_id` (FK), `clinic_id` (FK)
  - `date`, `notes`, `diagnosis`, `prescription`

- **Odontogram (Odontograma):**
  - `id` (PK, UUID), `patient_id` (FK), `clinic_id` (FK)
  - `tooth_number` (ISO 3950), `face` (vestibular, lingual, mesial, distal, oclusal), `status` (healthy, caries, filled, crown, missing, extraction_required), `updated_at`

- **Invoice (Factura / Comprobante):**
  - `id` (PK, UUID), `clinic_id` (FK), `patient_id` (FK)
  - `invoice_type` (C, B), `cae` (Código de Autorización Electrónica), `total_amount`, `status` (issued, voided), `created_at`

- **Payment / Transaction (Movimiento de Caja):** *(D-2)*
  - `id` (PK, UUID), `clinic_id` (FK), `patient_id` (FK), `invoice_id` (FK nullable a Invoice)
  - `method` (cash, transfer, mercadopago), `amount`, `status` (pending, reconciled, voided)
  - `idempotency_key` (UNIQUE, obligatoria para Mercado Pago y llamadas críticas AFIP), `created_at`
  - *Relación:* N:1 con `Invoice` (un pago puede no tener factura; una factura puede agrupar pagos). Separa cobro (Payment) de comprobante fiscal (Invoice).

- **Budget (Presupuesto básico MVP):** *(D-1)*
  - `id` (PK, UUID), `clinic_id` (FK), `patient_id` (FK), `medical_record_id` (FK nullable)
  - `status` (draft, pending, accepted, rejected, billed), `total_amount`, `created_at`
  - Sin firma digital en MVP (firma digital → V1.5 explícito).
  - *Relación:* 1:N con `BudgetItem`; al aceptar/billing genera ítems en cuenta corriente.

- **BudgetItem (Ítem de Presupuesto):** *(D-1)*
  - `id` (PK, UUID), `budget_id` (FK), `clinic_id` (FK)
  - `description`, `quantity`, `unit_price`, `subtotal`

- **AccountEntry (Cuenta Corriente del Paciente):** *(D-1)*
  - `id` (PK, UUID), `clinic_id` (FK), `patient_id` (FK), `budget_id` (FK nullable), `payment_id` (FK nullable)
  - `entry_type` (charge, payment), `amount`, `balance_after`, `created_at`

- **AuditLog (Auditoría):** *(exigido por RN-04; D-2/D-3)*
  - `id` (PK, UUID), `clinic_id` (FK), `actor_id` (FK a User nullable), `entity`, `entity_id`, `action`, `created_at`
  - Registra eventos (ej. confirmación/cancelación de turnos por WhatsApp). Sin datos sensibles de salud en el log (Ley 25.326).

## 2. Alcance y Notas de Versionado (D-1 → D-3)

- **Comisiones / liquidación de honorarios → V2 (sin entidad en MVP).** Solo cálculo como métrica; sin motor de liquidación automática (D-1).
- **Imágenes / Rx: MVP solo referencia/stub.** En MVP se guarda referencia (`image_url` / nota en `MedicalRecord`), sin PACS ni visor dedicado; gestión completa de imágenes → V2.
- **Multi-tenant v1 = clínica única (D-3):** todas las entidades llevan `clinic_id`; explícitamente **sin `branch_id`** en v1. Multi-sucursal (`Branch`) → V2.
