#!/bin/sh
set -eu

: "${POSTGRES_SEEDS:?POSTGRES_SEEDS is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PWD:?POSTGRES_PWD is required}"
: "${DBNAME:?DBNAME is required}"
: "${VISIBILITY_DBNAME:?VISIBILITY_DBNAME is required}"

export SQL_PASSWORD="${POSTGRES_PWD}"

echo "Waiting for PostgreSQL..."
until nc -z "${POSTGRES_SEEDS}" "${DB_PORT:-5432}"; do
  sleep 2
done

echo "Setting up Temporal main schema..."
temporal-sql-tool --plugin postgres12 --ep "${POSTGRES_SEEDS}" -u "${POSTGRES_USER}" -p "${DB_PORT:-5432}" --db "${DBNAME}" setup-schema -v 0.0
temporal-sql-tool --plugin postgres12 --ep "${POSTGRES_SEEDS}" -u "${POSTGRES_USER}" -p "${DB_PORT:-5432}" --db "${DBNAME}" update-schema -d /etc/temporal/schema/postgresql/v12/temporal/versioned

echo "Setting up Temporal visibility schema..."
temporal-sql-tool --plugin postgres12 --ep "${POSTGRES_SEEDS}" -u "${POSTGRES_USER}" -p "${DB_PORT:-5432}" --db "${VISIBILITY_DBNAME}" setup-schema -v 0.0
temporal-sql-tool --plugin postgres12 --ep "${POSTGRES_SEEDS}" -u "${POSTGRES_USER}" -p "${DB_PORT:-5432}" --db "${VISIBILITY_DBNAME}" update-schema -d /etc/temporal/schema/postgresql/v12/visibility/versioned

echo "Temporal PostgreSQL schema setup complete."
