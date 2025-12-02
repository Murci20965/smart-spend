#!/bin/bash
set -e

echo "📌 Starting Smart Spend API EntryPoint"

# STEP 1: Parse DATABASE_URL or use explicit env vars
if [ -n "$DATABASE_URL" ]; then
    DB_URL="${DATABASE_URL#*://}"
    DB_URL="${DB_URL#*@}"
    DB_HOST_PORT="${DB_URL%%/*}"
    DB_HOST="${DB_HOST_PORT%%:*}"
    DB_PORT="${DB_HOST_PORT#*:}"
    DB_PORT="${DB_PORT:-5432}"

    DB_USER_PASS="${DATABASE_URL#*://}"
    DB_USER_PASS="${DB_USER_PASS%%@*}"
    DB_USER="${DB_USER_PASS%%:*}"
    DB_NAME="${DB_URL#*/}"
    DB_NAME="${DB_NAME%%\?*}"
else
    DB_HOST="${POSTGRES_HOST:-postgres}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_USER="${POSTGRES_USER:-postgres}"
    DB_NAME="${POSTGRES_DB:-smart_spend}"
fi

# STEP 2: Wait for Postgres
echo "⏳ Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done
echo "✅ Postgres ready!"

# STEP 3: Run Alembic migrations
echo "🚀 Running Alembic migrations..."
alembic upgrade head
echo "✅ Alembic migrations completed!"

# STEP 4: Start API
echo "🚀 Starting Smart Spend API..."
exec "$@"
