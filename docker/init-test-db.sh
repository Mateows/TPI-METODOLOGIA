#!/bin/sh
# Runs once on first `db` init (docker-entrypoint-initdb.d): creates the
# isolated test database alongside POSTGRES_DB so `docker compose up -d db`
# alone provisions BOTH databases reproducibly.
set -e
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_TEST_DB:?POSTGRES_TEST_DB is required}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
SELECT 'CREATE DATABASE "${POSTGRES_TEST_DB}"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_TEST_DB}')\gexec
EOSQL
