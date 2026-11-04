# Spec Delta

## Purpose

Gestiona el padrón de pacientes de cada clínica odontológica, sus datos filiatorios y su resumen de anamnesis médica (`medical_history_summary`), asegurando aislamiento estricto por `clinic_id` y privacidad de datos sensibles de salud (RN-02, Ley 25.326).

## ADDED Requirements

### Requirement: Patient registration within clinic scope

The system SHALL allow authenticated clinic staff (`admin`, `receptionist`, `dentist`) to register a patient with personal data (`first_name`, `last_name`, `dni`, optional `email`, `phone`, `birth_date`) and optional `medical_history_summary` JSON, automatically binding the patient to the caller's `clinic_id`.

#### Scenario: Successful patient registration

- **WHEN** an authenticated staff member submits a valid patient creation request
- **THEN** the system persists the patient under the caller's `clinic_id` with `is_active = true` and UTC timestamps, and returns HTTP `201 Created` with the patient representation

#### Scenario: Client-supplied clinic_id is rejected

- **WHEN** a patient creation or update payload includes a `clinic_id` field
- **THEN** the system rejects the request with HTTP `422 Unprocessable Entity` and persists no changes

#### Scenario: Unauthenticated request is rejected

- **WHEN** an unauthenticated caller attempts to access any `/api/v1/patients` endpoint
- **THEN** the system responds with HTTP `401 Unauthorized`

### Requirement: Per-clinic DNI uniqueness

The system SHALL enforce uniqueness of the normalized patient `dni` within each clinic while allowing different clinics to register patients with the same `dni` without conflict or cross-tenant disclosure.

#### Scenario: Duplicate DNI within the same clinic is rejected

- **WHEN** an authenticated staff member attempts to create or update a patient with a `dni` already registered in the same clinic
- **THEN** the system rejects the operation with HTTP `409 Conflict` and error code `duplicate_dni`

#### Scenario: Same DNI in a different clinic is allowed

- **WHEN** an authenticated staff member registers a patient whose `dni` already exists in another clinic
- **THEN** the system creates the patient in the caller's clinic with HTTP `201 Created` and discloses no information about the other clinic

### Requirement: Tenant-isolated patient listing and search

The system SHALL allow authenticated clinic staff to list and search patients belonging exclusively to their active clinic, supporting case-insensitive filtering by `dni`, `first_name`, or `last_name`, active-status filtering, and pagination (`limit`, `offset`).

#### Scenario: Listing returns only patients of the caller's clinic

- **WHEN** an authenticated staff member requests `GET /api/v1/patients`
- **THEN** the system returns only patients matching the caller's `clinic_id` and never includes patients from other clinics

#### Scenario: Search filters by DNI or name within the clinic

- **WHEN** an authenticated staff member queries `GET /api/v1/patients?q=<term>`
- **THEN** the system returns only patients from the caller's clinic whose `dni`, `first_name`, or `last_name` matches `<term>`

### Requirement: Tenant-isolated patient retrieval

The system SHALL return a patient's detail only when the patient belongs to the caller's active clinic and SHALL respond to cross-clinic or non-existent patient identifiers with an indistinguishable `404 Not Found`.

#### Scenario: Retrieving an existing patient in the same clinic

- **WHEN** an authenticated staff member requests `GET /api/v1/patients/{id}` for a patient belonging to their clinic
- **THEN** the system returns HTTP `200 OK` with the patient's personal fields and `medical_history_summary`

#### Scenario: Retrieving a patient from another clinic returns 404

- **WHEN** an authenticated staff member requests `GET /api/v1/patients/{id}` for a patient belonging to a different clinic
- **THEN** the system responds with HTTP `404 Not Found` and code `not_found`, identical to a non-existent identifier

### Requirement: Patient partial update and logical deactivation

The system SHALL allow authenticated clinic staff to partially update a patient's personal data, `medical_history_summary`, or `is_active` status via `PATCH /api/v1/patients/{id}` within their clinic, refreshing `updated_at` in UTC without exposing physical deletion.

#### Scenario: Updating patient data and medical history summary

- **WHEN** an authenticated staff member submits `PATCH /api/v1/patients/{id}` with updated fields or `medical_history_summary` for a patient in their clinic
- **THEN** the system updates only the provided fields, refreshes `updated_at` in UTC, and returns HTTP `200 OK`

#### Scenario: Logical deactivation preserves clinical integrity

- **WHEN** an authenticated staff member sets `is_active = false` via `PATCH /api/v1/patients/{id}`
- **THEN** the patient record remains persisted in the database with `is_active = false` and is excluded from default active-only listings unless `include_inactive=true` is specified

#### Scenario: Updating a patient from another clinic returns 404

- **WHEN** an authenticated staff member submits `PATCH /api/v1/patients/{id}` targeting a patient from another clinic
- **THEN** the system responds with HTTP `404 Not Found` and modifies no data

### Requirement: Health data privacy and input validation

The system SHALL validate patient fields (`first_name`, `last_name`, normalized numeric/alphanumeric `dni`, non-future `birth_date`, and JSON object structure for `medical_history_summary`) and SHALL NOT write patient PII or `medical_history_summary` contents to application logs or error traces (RN-02, Ley 25.326).

#### Scenario: Invalid birth date or malformed medical history is rejected

- **WHEN** a caller submits a future `birth_date`, a blank `dni`, or a non-object `medical_history_summary`
- **THEN** the system rejects the request with HTTP `422 Unprocessable Entity`

#### Scenario: Error responses do not leak SQL traces or sensitive patient data

- **WHEN** a validation or domain error occurs during a patient operation
- **THEN** the response body follows the standard `{detail, code}` contract without database driver messages or sensitive health details
