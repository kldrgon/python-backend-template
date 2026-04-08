#!/bin/sh
set -eu

create_database_if_missing() {
  db_name="$1"
  if [ -z "${db_name}" ]; then
    return 0
  fi

  echo "Ensuring database '${db_name}' exists..."
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE "${db_name}"'
    WHERE NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '${db_name}'
    )\gexec
EOSQL
}

create_database_if_missing "${POSTGRES_APP_DB:-}"
create_database_if_missing "${POSTGRES_TEMPORAL_DB:-}"
create_database_if_missing "${POSTGRES_TEMPORAL_VISIBILITY_DB:-}"
