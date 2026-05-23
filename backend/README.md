# E-Library & Reading Intelligence API

Production MVP backend for student reading, librarian management, session tracking, and analytics.

## Stack

- Python / FastAPI
- PostgreSQL
- SQLAlchemy + Alembic
- JWT (python-jose) + bcrypt
- Docker + Gunicorn

## Quick Start

```bash
cd backend
cp .env.example .env
docker compose up --build
```

### Docker build fails pulling `python:3.12-slim`

If you see `lookup registry-1.docker.io ... i/o timeout`, Docker cannot reach Docker Hub (DNS/network). Try:

1. **Retry** when your connection is stable: `docker compose build --no-cache api`
2. **Pull manually**: `docker pull python:3.12-slim`
3. **Fix DNS** (Linux): set Docker DNS in `/etc/docker/daemon.json`:
   ```json
   { "dns": ["8.8.8.8", "1.1.1.1"] }
   ```
   Then `sudo systemctl restart docker`
4. **Workaround — infra in Docker, API on host**:
   ```bash
   docker compose -f docker-compose.infra.yml up -d
   # In .env set: DATABASE_URL=postgresql://elibrary:elibrary_secret@localhost:5432/elibrary
   ./scripts/run_local_api.sh
   ```
   Frontend: http://localhost:8080 · API: http://localhost:8000

API: `http://localhost:8000`  
Docs: `http://localhost:8000/api/docs`  
Health: `http://localhost:8000/health`

## Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Update DATABASE_URL for local PostgreSQL
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Serve the frontend (separate terminal):

```bash
cd ../frontend/src
python3 -m http.server 8080
```

Open http://localhost:8080 — the UI talks to http://localhost:8000 by default.

## Integration Tests

```bash
./scripts/run_tests.sh
# or
pytest tests/ -v
```

Tests use an in-memory SQLite database and a temporary upload directory.

## API Base Path

All routes are under `/api/v1`.

## Roles

- `STUDENT` — browse books, reading sessions, personal analytics
- `LIBRARIAN` — upload/delete books, dashboard, student analytics, exports

Authentication: `Authorization: Bearer <token>` from `POST /api/v1/auth/login`.
