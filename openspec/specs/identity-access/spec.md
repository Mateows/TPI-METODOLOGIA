# identity-access Specification

## Purpose

Permite que cada persona acceda al sistema con credenciales verificadas, una
sesión revocable y un rol explícito dentro de su clínica, y que un administrador
gestione los usuarios de su propia clínica.

## Requirements

### Requirement: Credential login

The system SHALL authenticate a user by email and password and SHALL issue a
short-lived access token plus a refresh token on success. Emails are unique
across the system, so authentication needs no clinic selector.

#### Scenario: Valid credentials issue a session

- **WHEN** an active user submits a registered email and the correct password
- **THEN** the system responds with an access token, a refresh token and the
  user's role, and no password material appears in the response

#### Scenario: Invalid credentials reveal nothing

- **WHEN** a request submits an unknown email or a wrong password
- **THEN** the system responds with the same generic authentication error for
  both cases and issues no token

### Requirement: Password storage

The system SHALL store only a salted, adaptive one-way hash of each password and
SHALL never return, log or transmit the plain password or the stored hash.

#### Scenario: Password never leaves the system

- **WHEN** a user is created and later authenticated
- **THEN** no endpoint response, error body or log entry contains the plain
  password or the stored hash

#### Scenario: Password is changeable by the owner

- **WHEN** an authenticated user supplies their current password and a valid
  new one
- **THEN** the system stores the new hash, revokes that user's other sessions
  and refuses the old password afterwards

### Requirement: Access token validity

The system SHALL accept an access token only while it is unexpired, unmodified
and belongs to an active user of an active clinic.

#### Scenario: Expired or tampered token is rejected

- **WHEN** a request presents an expired, altered or foreign-signed access token
- **THEN** the system responds with an authentication error and processes no
  data

#### Scenario: Deactivated user is rejected immediately

- **WHEN** a user is deactivated and then presents a still-unexpired access token
- **THEN** the system responds with an authentication error on that same request

### Requirement: Refresh session rotation

The system SHALL persist refresh tokens only as hashes, rotate them on each use
and treat reuse of an already-rotated token as a compromised session.

#### Scenario: Refresh rotates the token

- **WHEN** a client exchanges a valid refresh token for a new access token
- **THEN** the system returns a new refresh token and the previous one stops
  being usable

#### Scenario: Reused refresh token revokes the session

- **WHEN** a client presents a refresh token that was already rotated
- **THEN** the system rejects the request and revokes the whole session family

### Requirement: Logout revokes the session

The system SHALL revoke the caller's refresh session on logout so neither the
refresh token nor subsequent refreshes succeed.

#### Scenario: Logout ends the session

- **WHEN** an authenticated client logs out with its refresh token
- **THEN** the system revokes that session and later refresh attempts fail with
  an authentication error

### Requirement: Authenticated self-profile

The system SHALL expose the authenticated user's own profile and SHALL return
no other user's data through it.

#### Scenario: Profile reflects the authenticated session

- **WHEN** an authenticated client requests its own profile
- **THEN** the response contains only that user's identity, clinic and role, and
  no password hash, token or other user's data

#### Scenario: Profile cannot be targeted at another user

- **WHEN** a request attempts to read another user's profile through the
  self-profile endpoint
- **THEN** the system returns only the caller's profile and never the requested
  user's data

### Requirement: Intra-clinic user administration

The system SHALL allow only an authenticated `admin` to create, update and
deactivate users, and only within the administrator's own clinic. Roles are
limited to `admin`, `receptionist` and `dentist`.

#### Scenario: Admin creates a user in their clinic

- **WHEN** an authenticated admin submits a valid email, full name, role and
  initial password for a new user
- **THEN** the system creates the user assigned to the admin's clinic and
  returns it without credentials

#### Scenario: Non-admin cannot manage users

- **WHEN** a `receptionist` or `dentist` calls a user administration endpoint
- **THEN** the system responds with an authorization error and changes no user

#### Scenario: Duplicate email is rejected

- **WHEN** an admin submits a user whose email already belongs to an existing
  user
- **THEN** the system responds with a conflict error, creates no duplicate user
  and does not reveal which clinic owns that email

#### Scenario: Deactivated user cannot log in

- **WHEN** a user marked inactive submits correct credentials
- **THEN** the system responds with the generic authentication error and issues
  no token

### Requirement: No credential leakage in operational logs

The system SHALL record authentication failures and successes without including
passwords, tokens or patient-identifying content.

#### Scenario: Failed login is logged without secrets

- **WHEN** an authentication attempt fails
- **THEN** the resulting log entry contains no password, no token value and no
  clinical content
