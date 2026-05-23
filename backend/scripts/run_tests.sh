#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export DATABASE_URL="${DATABASE_URL:-sqlite://}"
export JWT_SECRET="${JWT_SECRET:-test-secret-key-for-integration-tests-only}"
export UPLOAD_DIRECTORY="${UPLOAD_DIRECTORY:-/tmp/libmetrics-test-uploads}"
mkdir -p "$UPLOAD_DIRECTORY"

python3 -m pip install -q -r requirements.txt
python3 -m pytest tests/ -v --tb=short
