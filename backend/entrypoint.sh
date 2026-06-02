#!/bin/sh
# entrypoint.sh

echo "Running database migrations..."
alembic upgrade head

echo "Starting Gunicorn..."
exec gunicorn app.main:app -c gunicorn.conf.py