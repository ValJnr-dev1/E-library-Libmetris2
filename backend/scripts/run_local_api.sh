#!/usr/bin/env bash
# Run API on host against Docker Postgres (infra compose must be up).
set -euo pipefail
cd "$(dirname "$0")/.."

export DATABASE_URL="${DATABASE_URL:-postgresql://elibrary:elibrary_secret@localhost:5432/elibrary}"
export JWT_SECRET="${JWT_SECRET:-dev-secret-change-in-production-min-32-chars}"
export UPLOAD_DIRECTORY="${UPLOAD_DIRECTORY:-./uploads}"
mkdir -p "$UPLOAD_DIRECTORY"

python3 -m pip install -q -r requirements.txt
python3 -m alembic upgrade head
exec python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
