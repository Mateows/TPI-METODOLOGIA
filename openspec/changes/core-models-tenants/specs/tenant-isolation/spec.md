# Spec Delta

## Purpose

Garantiza que cada petición autenticada opere sobre una única clínica y que
ninguna lectura ni escritura alcance datos de otra clínica (RN-02, Ley 25.326).

## ADDED Requirements

### Requirement: Server-derived clinic context

The system SHALL derive the active clinic from the authenticated identity on
every request and SHALL never trust a client-supplied clinic identifier as the
source of that context.

#### Scenario: Context comes from the token

- **WHEN** an authenticated request reaches a protected endpoint
- **THEN** the clinic scope is resolved from the verified session, not from a
  query parameter or body field

#### Scenario: Conflicting client clinic is rejected

- **WHEN** a request supplies a clinic identifier that differs from the
  authenticated clinic
- **THEN** the system rejects the request without applying any change

### Requirement: Tenant-scoped reads and writes

The system SHALL return and mutate only records whose `clinic_id` matches the
active clinic on every clinic-owned resource.

#### Scenario: Listing is filtered by clinic

- **WHEN** an authenticated user lists a clinic-owned resource
- **THEN** the response contains only records of the authenticated clinic

#### Scenario: Writing a foreign reference is rejected

- **WHEN** a request references an entity belonging to another clinic
- **THEN** the system rejects the request with a validation error and persists
  no record

### Requirement: Cross-clinic disclosure prevention

The system SHALL answer cross-clinic access attempts with an authorization or
not-found error that discloses neither the existence nor the content of the
other clinic's record.

#### Scenario: Foreign identifier is indistinguishable from absent

- **WHEN** a user requests a record identifier that belongs to another clinic
- **THEN** the response is the same shape and status as for a non-existent
  identifier and contains no record data

### Requirement: Role-based authorization guards

The system SHALL expose reusable authorization guards so protected endpoints
allow only the roles defined for their capability, and SHALL deny by default.

#### Scenario: Allowed role proceeds

- **WHEN** a user whose role is permitted for the endpoint calls it
- **THEN** the request is processed under the authenticated clinic context

#### Scenario: Forbidden role is denied before side effects

- **WHEN** a user whose role is not permitted calls the endpoint
- **THEN** the system responds with an authorization error and no record is
  created or modified

### Requirement: Inactive clinic denies access

The system SHALL refuse authenticated access when the user's clinic is inactive,
even if the user account is otherwise valid.

#### Scenario: Inactive clinic cannot operate

- **WHEN** a user of an inactive clinic presents a valid session
- **THEN** the system responds with an authorization error and returns no
  clinic data

### Requirement: Operator-only clinic provisioning

The system SHALL provision the first clinic and its administrator through an
idempotent operator command and SHALL NOT expose a public endpoint that creates
clinics.

#### Scenario: Bootstrap is idempotent

- **WHEN** the operator runs the provisioning command twice with the same input
- **THEN** the second run creates no duplicate clinic or user and reports the
  existing state

#### Scenario: No public clinic creation

- **WHEN** an unauthenticated caller attempts to create a clinic through the API
- **THEN** the system exposes no such route and creates nothing
