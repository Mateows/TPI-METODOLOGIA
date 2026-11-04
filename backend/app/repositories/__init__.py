"""Persistence layer (design D13).

Every SQLAlchemy query or write lives here; services and the CLI only
orchestrate business rules. Repositories ``flush`` but never ``commit``: the
transaction boundary stays in the router (or in the service for the revocation
paths that must survive an error response, design D3). Clinic-scoped reads take
``clinic_id`` explicitly (design D5); global lookups are named as such.
"""
