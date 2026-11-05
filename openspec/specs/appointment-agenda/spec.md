# appointment-agenda Specification

## Purpose
Permite administrar boxes y turnos de una clínica de forma segura, evitando
solapamientos y conservando estados y horarios consistentes para la agenda.

## Requirements

### Requirement: Agenda clinic scope is server-derived

The system SHALL derive the persisted `clinic_id` of every box and appointment
exclusively from the authenticated context (verified session plus reload from the
database, as defined in `tenant-isolation`), and SHALL reject any payload that
supplies a clinic identifier.

#### Scenario: Payload cannot set clinic_id

- **WHEN** a request to create a box or an appointment includes a `clinic_id`
  field in the body, whether it matches the authenticated clinic or not
- **THEN** the system rejects the request with a `422 validation_error` and
  persists no record

#### Scenario: Record belongs to the authenticated clinic

- **WHEN** an authorized user of a clinic creates a box or a valid appointment
  without sending any clinic field
- **THEN** the stored record carries the `clinic_id` of the authenticated
  context and is not retrievable from any other clinic

### Requirement: Box isolation

The system SHALL associate every box with one clinic and SHALL only expose boxes
belonging to the authenticated clinic.

#### Scenario: Box is listed for its clinic

- **WHEN** an authenticated user requests the active boxes of their clinic
- **THEN** the response contains only boxes whose `clinic_id` matches the
  authenticated clinic context

#### Scenario: Cross-clinic box is not accessible

- **WHEN** a user requests a box identifier belonging to another clinic
- **THEN** the system responds with the same `404 not_found` result as for a
  non-existent box, without disclosing whether the box exists or any of its data

### Requirement: Box creation

The system SHALL create a box assigned to the authenticated clinic with a
non-empty name.

#### Scenario: Box is created in the authenticated clinic

- **WHEN** an authorized user submits a valid box name without any clinic field
- **THEN** the system persists the box with the `clinic_id` of the authenticated
  context and returns it

### Requirement: Appointment creation

The system SHALL create a `scheduled` appointment only when the patient,
`dentist_id` and box belong to the authenticated clinic, `end_time` is after
`start_time`, and both datetimes are timezone-aware. Datetimes SHALL be
normalized to UTC before persisting.

#### Scenario: Valid appointment is scheduled

- **WHEN** valid clinic-owned references and two timezone-aware datetimes with
  `end_time > start_time` are submitted
- **THEN** the system normalizes both datetimes to UTC, creates one appointment
  with status `scheduled` and the `clinic_id` of the authenticated context

#### Scenario: Invalid time range is rejected

- **WHEN** an appointment is submitted with `end_time` equal to or before
  `start_time`
- **THEN** the system rejects the request with a semantic business validation
  error and persists no appointment

#### Scenario: Naive datetime is rejected

- **WHEN** an appointment is submitted with a `start_time` or `end_time` that
  carries no timezone information
- **THEN** the system rejects the request with a `422 validation_error` and
  persists no appointment, instead of assuming a default timezone

#### Scenario: Offset datetime is normalized to UTC

- **WHEN** an appointment is submitted with `start_time` and `end_time` carrying
  an offset of `-03:00`
- **THEN** the system persists the equivalent UTC instants and returns them as
  UTC datetimes

### Requirement: Overlap prevention

The system SHALL reject an appointment that overlaps an existing non-cancelled
appointment for the same `dentist_id` or the same `box_id`, within the
authenticated clinic. Overlap SHALL be evaluated with the open interval
`existing.start_time < new.end_time` and
`existing.end_time > new.start_time`, so appointments that only share a boundary
are allowed.

#### Scenario: Dentist overlap is rejected

- **WHEN** a new appointment overlaps an existing appointment for the same
  `dentist_id`
- **THEN** the system returns a conflict error and does not create the new
  appointment

#### Scenario: Box overlap is rejected

- **WHEN** a new appointment overlaps an existing appointment for the same
  `box_id`, even if the `dentist_id` differs
- **THEN** the system returns a conflict error and does not create the new
  appointment

#### Scenario: Contained appointment is rejected

- **WHEN** a new appointment starts after another existing appointment for the
  same `dentist_id` or `box_id` and ends before that appointment ends
- **THEN** the system returns a conflict error and does not create the new
  appointment

#### Scenario: Exact interval match is rejected

- **WHEN** a new appointment has exactly the same `start_time` and `end_time` as
  an existing appointment for the same `dentist_id` or `box_id`
- **THEN** the system returns a conflict error and does not create the new
  appointment

#### Scenario: Consecutive intervals do not overlap

- **WHEN** an appointment starts exactly when another appointment for the same
  `dentist_id` or `box_id` ends
- **THEN** the system accepts it if all other validations pass

#### Scenario: Cancelled appointment frees the interval

- **WHEN** a new appointment overlaps only appointments in status `cancelled`
  for the same `dentist_id` or `box_id`
- **THEN** the system accepts it if all other validations pass, because
  cancelled appointments do not participate in overlap detection

### Requirement: Appointment states

The system SHALL allow only the states `scheduled`, `confirmed`, `attended`,
`cancelled` and `no_show`. Reading or changing a foreign-clinic appointment
SHALL behave as `404 not_found`.

#### Scenario: Unknown state is rejected

- **WHEN** a request attempts to set a state outside `scheduled`, `confirmed`,
  `attended`, `cancelled` or `no_show`
- **THEN** the system rejects the request with a validation error and keeps the
  previous state

#### Scenario: Cross-clinic appointment change is not found

- **WHEN** a user attempts to change the state of an appointment belonging to
  another clinic
- **THEN** the system responds with the same `404 not_found` result as for a
  non-existent appointment and changes nothing

### Requirement: Appointment transition matrix

The system SHALL apply only the transitions `scheduled`→`confirmed`,
`scheduled`→`cancelled`, `confirmed`→`attended` and `confirmed`→`cancelled`.
The origin of `no_show` and any other transition remain open decisions recorded
in `design.md` and MUST NOT be inferred during implementation.

#### Scenario: Scheduled appointment is confirmed

- **WHEN** an authorized clinic user changes a `scheduled` appointment to
  `confirmed`
- **THEN** the system persists the new state and returns the updated appointment

#### Scenario: Undeclared transition is rejected

- **WHEN** a request attempts a transition that is not declared above, for
  example `cancelled` to `confirmed` or `attended` to `scheduled`
- **THEN** the system rejects the request with a business conflict error and
  preserves the previous state

### Requirement: Appointment read isolation

The system SHALL list and read appointments only for the authenticated clinic
and SHALL accept an optional inclusive date range filter over `start_time`.

#### Scenario: Appointment listing is filtered by clinic

- **WHEN** an authorized user lists appointments for a date range
- **THEN** the response contains only appointments whose `clinic_id` matches the
  authenticated clinic and whose `start_time` falls inside the requested range

#### Scenario: Cross-clinic appointment read is indistinguishable from absent

- **WHEN** a user requests an appointment identifier belonging to another clinic
- **THEN** the system responds with the same `404 not_found` result as for a
  non-existent appointment and returns no appointment data
