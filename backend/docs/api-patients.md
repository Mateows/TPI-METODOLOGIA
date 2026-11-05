# API de gestión de pacientes (`/api/v1/patients`)

Estado: **C-03 (`patient-management`)**. Esta página documenta los endpoints REST
del padrón de pacientes por clínica, la estructura del resumen de anamnesis médica
(`medical_history_summary`), los parámetros de búsqueda y el contrato de errores.

Todos los valores de los ejemplos son ficticios. En cumplimiento de la **Ley 25.326**
(RN-02), el servidor jamás registra DNI, nombres, contacto ni `medical_history_summary`
en logs ni en respuestas de error.

## Convenciones y aislamiento multi-tenant

| Aspecto | Valor |
|---|---|
| Base URL de desarrollo | `http://localhost:8000` |
| Prefijo | `/api/v1/patients` |
| Formato | JSON (`Content-Type: application/json`) |
| Autorización | `Authorization: Bearer <access_token>` |
| Roles permitidos | `admin`, `receptionist`, `dentist` |
| Aislamiento multi-tenant | Estricto por `clinic_id` derivado del `Principal` autenticado |
| Fechas persistidas | `created_at` y `updated_at` en UTC (`DateTime(timezone=True)`) |
| Baja de pacientes | Lógica (`is_active = false` vía `PATCH`); no existe `DELETE` físico |

- El cliente **nunca** envía `clinic_id` en el cuerpo de creación o actualización
  (`extra="forbid"`): cualquier intento responde `422 validation_error` sin persistir cambios.
- El `dni` se normaliza quitando espacios y puntos separadores (ej. `" 30.111.222 "` → `"30111222"`)
  y es único **dentro de cada clínica** (`UniqueConstraint("clinic_id", "dni")`). Dos clínicas
  distintas pueden registrar a la misma persona física sin conflicto ni revelación entre tenants.
- El `email`, si se informa, se normaliza a minúsculas.
- `birth_date`, si se informa, no puede ser una fecha futura.

## Estructura de `medical_history_summary`

El campo opcional `medical_history_summary` almacena la anamnesis médica resumida del
paciente como un objeto JSON (`dict[str, Any] | None`). Valores primitivos o listas en
la raíz son rechazados con `422 validation_error`.

Ejemplo de estructura recomendada:

```json
{
  "allergies": ["penicilina", "latex"],
  "medications": ["losartan 50mg"],
  "conditions": ["hipertension"],
  "smoker": false,
  "notes": "Requiere profilaxis antibiótica previa a cirugía"
}
```

## Contrato de errores

Toda falla responde `{ "detail": "...", "code": "..." }`, sin exponer trazas SQL,
nombres de constraints ni datos sensibles (Ley 25.326).

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `authentication_failed` | falta `Authorization: Bearer <token>`, o el token es inválido/expirado/de usuario inactivo |
| 403 | `forbidden` | la clínica del usuario autenticado está inactiva o el rol no tiene permiso |
| 404 | `not_found` | el paciente no existe o pertenece a otra clínica (`detail: "resource not found"`, indistinguible) |
| 409 | `duplicate_dni` | ya existe un paciente con ese `dni` en la clínica activa |
| 422 | `validation_error` | cuerpo o parámetros inválidos (`clinic_id` inyectado, `dni` vacío, `birth_date` futura, `medical_history_summary` no-objeto) |

---

## `POST /api/v1/patients`

Registra un paciente nuevo en la clínica activa del usuario autenticado (`admin`,
`receptionist` o `dentist`).

### Request

```bash
curl -i -X POST http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Valeria",
    "last_name": "Acosta",
    "dni": "34.555.666",
    "email": "valeria.acosta@example.com",
    "phone": "+54 9 11 1111-2222",
    "birth_date": "1988-11-20",
    "medical_history_summary": {
      "allergies": ["aspirina"],
      "diabetic": false
    }
  }'
```

### Response `201 Created`

```json
{
  "id": "b7f2c9a1-4e8d-4b2a-9c1d-8f3e2a1b4c5d",
  "clinic_id": "6d1c9e2a-3b4f-4c8d-8e7a-1f2a3b4c5555",
  "first_name": "Valeria",
  "last_name": "Acosta",
  "dni": "34555666",
  "email": "valeria.acosta@example.com",
  "phone": "+54 9 11 1111-2222",
  "birth_date": "1988-11-20",
  "medical_history_summary": {
    "allergies": ["aspirina"],
    "diabetic": false
  },
  "is_active": true,
  "created_at": "2026-11-04T21:00:00Z",
  "updated_at": "2026-11-04T21:00:00Z"
}
```

---

## `GET /api/v1/patients`

Lista o busca pacientes pertenecientes exclusivamente a la clínica activa del
usuario autenticado, ordenados por `last_name ASC, first_name ASC, id ASC`.

### Parámetros de query

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `q` | `string \| null` | `null` | Búsqueda case-insensitive por coincidencia parcial en `dni`, `first_name` o `last_name` (máx. 120 caracteres) |
| `include_inactive` | `boolean` | `false` | Si es `false`, devuelve sólo pacientes con `is_active = true`; si es `true`, incluye dados de baja lógica |
| `limit` | `integer` | `50` | Cantidad máxima de resultados (`1` a `100`) |
| `offset` | `integer` | `0` | Desplazamiento para paginación (`>= 0`) |

### Request

```bash
curl -i "http://localhost:8000/api/v1/patients?q=acosta&include_inactive=false&limit=50&offset=0" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia"
```

### Response `200 OK`

```json
[
  {
    "id": "b7f2c9a1-4e8d-4b2a-9c1d-8f3e2a1b4c5d",
    "clinic_id": "6d1c9e2a-3b4f-4c8d-8e7a-1f2a3b4c5555",
    "first_name": "Valeria",
    "last_name": "Acosta",
    "dni": "34555666",
    "email": "valeria.acosta@example.com",
    "phone": "+54 9 11 1111-2222",
    "birth_date": "1988-11-20",
    "medical_history_summary": {
      "allergies": ["aspirina"],
      "diabetic": false
    },
    "is_active": true,
    "created_at": "2026-11-04T21:00:00Z",
    "updated_at": "2026-11-04T21:00:00Z"
  }
]
```

---

## `GET /api/v1/patients/{id}`

Obtiene el detalle completo de un paciente de la clínica activa. Si el `id` no
existe o pertenece a otra clínica, responde `404 Not Found` (`code: "not_found"`).

### Request

```bash
curl -i http://localhost:8000/api/v1/patients/b7f2c9a1-4e8d-4b2a-9c1d-8f3e2a1b4c5d \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia"
```

### Response `200 OK`

Devuelve el objeto `PatientResponse` completo.

---

## `PATCH /api/v1/patients/{id}`

Actualiza parcialmente los datos filiatorios, `medical_history_summary` o el
estado `is_active` de un paciente de la clínica activa, refrescando `updated_at`
en UTC. Si el paciente pertenece a otra clínica o no existe, responde `404 Not Found`
sin modificar datos. Si el nuevo `dni` colisiona con otro paciente de la misma
clínica, responde `409 Conflict` (`code: "duplicate_dni"`).

### Request

```bash
curl -i -X PATCH http://localhost:8000/api/v1/patients/b7f2c9a1-4e8d-4b2a-9c1d-8f3e2a1b4c5d \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ejemplo.firma-ficticia" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+54 11 2222-3333",
    "medical_history_summary": {
      "allergies": ["aspirina"],
      "conditions": ["hipertension"]
    },
    "is_active": false
  }'
```

### Response `200 OK`

Devuelve el objeto `PatientResponse` actualizado.
