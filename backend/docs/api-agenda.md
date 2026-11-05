# API de Boxes y Turnos (`/api/v1/boxes` y `/api/v1/appointments`)

Estado: **C-04 (`appointment-agenda`)**. Esta página documenta los endpoints REST
de boxes y agenda de turnos odontológicos, las reglas de prevención de solapamiento (RN-01),
el formato de persistencia y normalización UTC (RN-07), la matriz de estados y el contrato
de errores.

Todos los valores de los ejemplos son ficticios y reproducibles sin datos reales. En cumplimiento
de la **Ley 25.326**, el servidor jamás registra datos identificatorios de pacientes en logs ni en
respuestas de error.

---

## Convenciones y aislamiento multi-tenant

| Aspecto | Valor |
|---|---|
| Base URL de desarrollo | `http://localhost:8000` |
| Prefijos | `/api/v1/boxes` y `/api/v1/appointments` |
| Formato | JSON (`Content-Type: application/json`) |
| Autorización | `Authorization: Bearer <access_token>` |
| Roles en Boxes | Creación: solo `admin`; Lectura: `admin`, `receptionist`, `dentist` |
| Roles en Appointments | Creación, lectura y actualización: `admin`, `receptionist`, `dentist` |
| Aislamiento multi-tenant | Estricto por `clinic_id` derivado exclusivamente del `Principal` autenticado |
| Fechas persistidas | Fechas y horas en UTC (`DateTime(timezone=True)`) |

- El cliente **nunca** envía `clinic_id` en el cuerpo de las solicitudes (`extra="forbid"`):
  cualquier intento responde `422 validation_error` sin persistir ningún registro.
- Todo recurso de otra clínica responde `404 not_found` (indistinguible de un identificador inexistente).

---

## Formato y consistencia temporal (RN-07)

- Los campos `start_time` y `end_time` en las solicitudes de turnos **deben** ser timezone-aware (ej. `2026-11-10T10:00:00Z` o `2026-11-10T07:00:00-03:00`).
- Cualquier datetime naive (sin zona horaria) es rechazado con `422 validation_error`.
- Los datetimes con offset (ej. `-03:00`) se normalizan automáticamente a su instante UTC equivalente antes de persistir.
- `end_time` debe ser estrictamente posterior a `start_time` (`end_time > start_time`); intervalos nulos o negativos son rechazados con `422 invalid_time_range`.

---

## Prevención de solapamientos y concurrencia (RN-01)

El sistema rechaza la creación de un turno si colisiona con otro turno existente no cancelado
en la misma clínica para el mismo odontólogo (`dentist_id`) **o** el mismo box (`box_id`).

El solapamiento se evalúa con el intervalo abierto:
```text
existing.start_time < new.end_time AND existing.end_time > new.start_time
```

- **Garantía ante concurrencia**: Se implementa serialización mediante bloqueo de recursos (`with_for_update`) sobre el odontólogo y el box en repositorio/servicio. Como salvaguarda de base de datos a nivel de motor en PostgreSQL, la tabla `appointments` define restricciones de exclusión `EXCLUDE USING gist` sobre `(clinic_id, dentist_id, tstzrange)` y `(clinic_id, box_id, tstzrange)` cuando el estado no es cancelado.
- **Turnos contiguos**: Permitidos (`existing.end_time == new.start_time`).
- **Turnos cancelados**: Los turnos en estado `cancelled` no participan en el chequeo de solapamiento y liberan el intervalo.
- **Colisión detectada**: Responde `409 appointment_overlap`.

---

## Matriz de estados y transiciones

Estados posibles: `scheduled`, `confirmed`, `attended`, `cancelled`, `no_show`.

Todo turno nuevo se crea en estado inicial `scheduled`.

Las transiciones válidas permitidas son:
- `scheduled` → `confirmed`
- `scheduled` → `cancelled`
- `confirmed` → `attended`
- `confirmed` → `cancelled`

Cualquier otra transición es rechazada con `409 invalid_appointment_transition`.
Cualquier estado desconocido es rechazado con `422 validation_error`.

---

## Endpoints de Boxes (`/api/v1/boxes`)

### `POST /api/v1/boxes`
Crea un box en la clínica del usuario autenticado (requiere rol `admin`).

**Request body:**
```json
{
  "name": "Box 1"
}
```

**Response `201 Created`:**
```json
{
  "id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
  "name": "Box 1",
  "status": "active"
}
```

### `GET /api/v1/boxes`
Lista todos los boxes de la clínica activa.

**Response `200 OK`:**
```json
[
  {
    "id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
    "name": "Box 1",
    "status": "active"
  }
]
```

### `GET /api/v1/boxes/{id}`
Obtiene el detalle de un box individual de la clínica activa. Un ID perteneciente a otra clínica responde `404 not_found` idéntico a inexistente.

**Response `200 OK`:**
```json
{
  "id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
  "name": "Box 1",
  "status": "active"
}
```

---

## Endpoints de Turnos (`/api/v1/appointments`)

### `POST /api/v1/appointments`
Agenda un nuevo turno validando referencias, rango horario y solapamiento.

**Request body:**
```json
{
  "patient_id": "c1a1796d-88f1-41b4-b0db-6e119934e620",
  "dentist_id": "a50c822e-1311-4770-9852-53bfa5981140",
  "box_id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
  "start_time": "2026-11-10T10:00:00Z",
  "end_time": "2026-11-10T10:30:00Z",
  "notes": "Consulta inicial de diagnóstico"
}
```

**Response `201 Created`:**
```json
{
  "id": "b7849cb1-55cc-44a6-9bb2-bf02a4bf772a",
  "clinic_id": "9d1b7425-4560-449e-876a-b6059d0840f1",
  "patient_id": "c1a1796d-88f1-41b4-b0db-6e119934e620",
  "dentist_id": "a50c822e-1311-4770-9852-53bfa5981140",
  "box_id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
  "start_time": "2026-11-10T10:00:00Z",
  "end_time": "2026-11-10T10:30:00Z",
  "status": "scheduled",
  "notes": "Consulta inicial de diagnóstico",
  "created_at": "2026-11-05T04:00:00Z",
  "updated_at": "2026-11-05T04:00:00Z"
}
```

### `GET /api/v1/appointments`
Lista turnos de la clínica con filtros opcionales de rango de fechas y estado.

**Query Parameters:**
- `start_time` (opcional): Filtro datetime inferior (inclusivo).
- `end_time` (opcional): Filtro datetime superior (inclusivo).
- `status` (opcional): Filtro por estado (`scheduled`, `confirmed`, `attended`, `cancelled`, `no_show`).

**Response `200 OK`:**
```json
[
  {
    "id": "b7849cb1-55cc-44a6-9bb2-bf02a4bf772a",
    "clinic_id": "9d1b7425-4560-449e-876a-b6059d0840f1",
    "patient_id": "c1a1796d-88f1-41b4-b0db-6e119934e620",
    "dentist_id": "a50c822e-1311-4770-9852-53bfa5981140",
    "box_id": "e6f42b6a-939e-4e4b-88a4-071a938c3501",
    "start_time": "2026-11-10T10:00:00Z",
    "end_time": "2026-11-10T10:30:00Z",
    "status": "scheduled",
    "notes": "Consulta inicial de diagnóstico",
    "created_at": "2026-11-05T04:00:00Z",
    "updated_at": "2026-11-05T04:00:00Z"
  }
]
```

### `GET /api/v1/appointments/{id}`
Obtiene el detalle de un turno por su identificador.

**Response `200 OK`:** objeto `AppointmentResponse`.

### `PATCH /api/v1/appointments/{id}/status`
Actualiza el estado de un turno siguiendo la matriz de transiciones.

**Request body:**
```json
{
  "status": "confirmed"
}
```

**Response `200 OK`:** objeto `AppointmentResponse` con el nuevo estado.

---

## Contrato de errores

Toda falla responde `{ "detail": "...", "code": "..." }`:

| HTTP | `code` | Cuándo ocurre |
|---|---|---|
| 401 | `authentication_failed` | Falta token de autenticación o es inválido/expirado |
| 403 | `forbidden` | Rol no autorizado o clínica inactiva |
| 404 | `not_found` | El turno, paciente, odontólogo o box no existe en la clínica activa |
| 409 | `appointment_overlap` | El intervalo colisiona con otro turno para el mismo odontólogo o box (RN-01) |
| 409 | `invalid_appointment_transition` | Transición de estado no permitida por la matriz |
| 422 | `invalid_time_range` | `end_time` es igual o anterior a `start_time` (RN-07) |
| 422 | `validation_error` | Datetime naive, payload con `clinic_id`, o estado desconocido |
| 500 | `internal_error` | Falla interna inesperada sin filtración de trazas |
