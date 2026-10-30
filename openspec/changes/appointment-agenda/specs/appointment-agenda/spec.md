# Spec Delta

## Purpose

Permite administrar boxes y turnos de una clínica de forma segura, evitando
solapamientos y conservando estados y horarios consistentes para la agenda.

## ADDED Requirements

### Requirement: Box isolation

The system SHALL associate every box with one clinic and SHALL only expose boxes
belonging to the authenticated clinic.

#### Scenario: Box is listed for its clinic

- **WHEN** an authenticated user requests the active boxes of their clinic
- **THEN** the response contains only boxes whose `clinic_id` matches the
  authenticated clinic context

#### Scenario: Cross-clinic box is not accessible

- **WHEN** a user requests a box belonging to another clinic
- **THEN** the system returns a not-found or authorization error without
  disclosing the box data

### Requirement: Appointment creation

The system SHALL create a scheduled appointment only when the patient,
professional and box belong to the same clinic and the end time is after the
start time.

#### Scenario: Valid appointment is scheduled

- **WHEN** valid clinic-owned references and a UTC interval with
  `end_time > start_time` are submitted
- **THEN** the system creates one appointment with status `scheduled`

#### Scenario: Invalid time range is rejected

- **WHEN** an appointment is submitted with `end_time` equal to or before
  `start_time`
- **THEN** the system rejects the request with a semantic business validation
  error and persists no appointment

### Requirement: Overlap prevention

The system SHALL reject an appointment that overlaps an existing non-cancelled
appointment for the same professional or the same box.

#### Scenario: Professional overlap is rejected

- **WHEN** a new appointment overlaps an existing appointment for the same
  professional
- **THEN** the system returns a conflict error and does not create the new
  appointment

#### Scenario: Boundary intervals do not overlap

- **WHEN** an appointment starts exactly when another appointment for the same
  professional ends
- **THEN** the system accepts it if all other validations pass

### Requirement: Appointment state transitions

The system SHALL allow only defined agenda states and SHALL preserve clinic
isolation when reading or changing an appointment.

#### Scenario: Appointment is confirmed

- **WHEN** an authorized clinic user changes a scheduled appointment to
  `confirmed`
- **THEN** the system persists the new state and returns the updated appointment

#### Scenario: Unknown state is rejected

- **WHEN** a request attempts to set a state outside `scheduled`, `confirmed`,
  `attended`, `cancelled` or `no_show`
- **THEN** the system rejects the request with a validation error and keeps the
  previous state
