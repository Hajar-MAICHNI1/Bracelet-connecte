#!/bin/bash
set -e

echo "Starting IoT Backend setup..."

# 1. Export credentials safely from App Service Environment Variables
# Azure App Service usually provides these if you set them in Configuration
# We default to the values you provided ONLY if vars are missing (for safety)
: "${DB_HOST:=braceletbd.postgres.database.azure.com}"
: "${DB_USER:=admin_iotdb}"
: "${DB_NAME:=postgres}" 
# NOTE: We assume PGPASSWORD is set in Azure Env Vars. 
# If not, the script might fail here.

echo "Waiting for PostgreSQL to be ready at $DB_HOST..."

# 2. Correct usage of pg_isready
# We rely on PGPASSWORD env var being set for authentication
until pg_isready -h "$DB_HOST" -p 5432 -U "$DB_USER" -d "$DB_NAME"; do
  echo "PostgreSQL is unavailable - sleeping 5s"
  sleep 5
done

echo "PostgreSQL is up and running!"

# 3. Run migrations
echo "Running database migrations..."
# Ensure the connection string uses the URL-encoded password if strictly necessary
# But better to rely on DATABASE_URL env var
uv run alembic upgrade head

echo "Database migrations completed successfully!"

# 4. Start the application
echo "Starting FastAPI application..."
exec "$@"