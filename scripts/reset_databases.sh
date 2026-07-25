#!/usr/bin/env bash

set -euo pipefail

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-bmw-agent-postgres}"
API_CONTAINER="${API_CONTAINER:-bmw-agent-api}"
APP_DB="${APP_DB:-bmw_agent_app}"
TEST_DB="${TEST_DB:-bmw_agent_test}"
DB_USER="${DB_USER:-bmw_agent}"

reset_schema() {
  local db_name="$1"
  echo "Resetting schema in database: ${db_name}"
  docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${db_name}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
}

database_exists() {
  local db_name="$1"
  docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db_name}'" | grep -q '^1$'
}

echo "Checking required containers..."
docker exec "${POSTGRES_CONTAINER}" true >/dev/null
docker exec "${API_CONTAINER}" true >/dev/null

reset_schema "${APP_DB}"

if database_exists "${TEST_DB}"; then
  reset_schema "${TEST_DB}"
else
  echo "Skipping missing test database: ${TEST_DB}"
fi

echo "Running Alembic migrations for application database..."
docker exec "${API_CONTAINER}" alembic upgrade head

echo "Recreating test database schema via pytest fixture setup..."
if database_exists "${TEST_DB}"; then
  docker exec "${API_CONTAINER}" pytest tests/test_test_database_safety.py -q >/dev/null
fi

echo "Verification: row counts in key application tables"
for table_name in campaign dealer campaign_dealer_contact inbound_email dealer_offer; do
  docker exec "${POSTGRES_CONTAINER}" psql -U "${DB_USER}" -d "${APP_DB}" -v ON_ERROR_STOP=1 -c "SELECT '${table_name}' AS table_name, COUNT(*) AS row_count FROM public.${table_name};"
done

echo "Database reset completed."
