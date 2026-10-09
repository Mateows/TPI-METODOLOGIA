# backend-foundation Specification

## Purpose

Establish a runnable, testable backend baseline so all later clinical changes build on verified app boot, database, and test infrastructure.

## Requirements

### Requirement: Application boots from environment configuration

The system SHALL start the API from environment-provided configuration and SHALL fail fast with a clear error when a required variable is missing, without requiring code changes per environment.

#### Scenario: Boot with valid configuration

- **WHEN** all required environment variables are set and the operator starts the API
- **THEN** the application becomes ready to serve requests without code changes

#### Scenario: Missing required variable fails fast

- **WHEN** a required variable (e.g. database URL or secret key) is absent
- **THEN** startup fails with an error naming the missing variable and no partial serving occurs

### Requirement: Health endpoint reports liveness and database reachability

The system SHALL expose an unauthenticated `GET /health` endpoint that returns service liveness and database connectivity status.

#### Scenario: Healthy system

- **WHEN** a client calls `GET /health` with the database reachable
- **THEN** the system responds `200` with a payload indicating healthy status for both app and database

#### Scenario: Database unreachable

- **WHEN** a client calls `GET /health` while the database is unreachable
- **THEN** the system responds with a non-healthy database status (non-`200` or explicit unhealthy payload)

### Requirement: Database is provisioned and migrated reproducibly

The system SHALL provide a reproducible local database via container orchestration, and all schema state SHALL be reachable by applying versioned migrations from an empty database.

#### Scenario: Fresh provision from empty state

- **WHEN** an operator provisions containers and applies migrations from an empty database
- **THEN** the database reaches the current schema with no manual SQL and the API connects successfully

#### Scenario: Migration chain is ordered and repeatable

- **WHEN** migrations are applied twice in sequence (second run on an up-to-date database)
- **THEN** the second run is a no-op and reports no pending migrations

### Requirement: Test harness runs against an isolated test database

The system SHALL provide a test harness that executes the full suite against an isolated test database, never the development database, with per-test transactional isolation.

#### Scenario: Full suite passes in isolation

- **WHEN** the operator runs the test suite with the test database configured
- **THEN** all tests pass and no data is written to the development database

#### Scenario: No health data in logs

- **WHEN** any test exercises API or database paths with patient-like data
- **THEN** no patient-identifying or clinical content appears in captured logs (per Ley 25.326 logging prohibition)
