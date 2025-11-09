#!/bin/sh

# Wait for the database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready."

# Run the database initialization script (it's safe to run every time now)
echo "Checking/creating database tables..."
python -m app.db_init

# Execute the main command (passed from docker-compose)
exec "$@"
