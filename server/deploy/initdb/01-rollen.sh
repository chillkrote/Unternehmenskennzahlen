#!/bin/sh
# Läuft einmal beim ersten Start einer leeren Datenbank (docker-entrypoint-initdb.d).
# Rolle sphaerae_api: darf sich anmelden und nur lesen. Leserechte vergibt etl.laden nach jeder Migration (rechte_vergeben).
set -eu
psql -v ON_ERROR_STOP=1 --username postgres --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE sphaerae_api LOGIN PASSWORD '${SPHAERAE_API_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER ROLE sphaerae_api SET default_transaction_read_only = on;
ALTER ROLE sphaerae_api SET statement_timeout = '10s';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
