#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Run migrations before starting the app (safe to run repeatedly).
python -m alembic upgrade head

# Start gunicorn
exec gunicorn app.main:app -c gunicorn.conf.py
