#!/bin/bash

# Setup script for IoT Backend
# This script runs alembic migrations after the backend container is up and healthy

set -e

echo "Starting IoT Backend setup..."

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U $POSTGRES_USER -d $POSTGRES_DB; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 10
done

echo "PostgreSQL is up and running!"

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

echo "Database migrations completed successfully!"

# Start the application
echo "Starting FastAPI application..."
exec "$@"