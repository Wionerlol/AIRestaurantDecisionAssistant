# AI Restaurant Decision Assistant

Monorepo for an AI restaurant assistant. The current backend state focuses on two foundations:

- a database-backed restaurant data service
- a minimal LangChain / LangGraph chat loop

## Structure

- `backend/`: FastAPI service on Python 3.12
- `frontend/`: Next.js app shell
- `docker/`: Container definitions and compose file
- `scripts/`: Local helper scripts
- `skills/`: Placeholder for reusable prompt/workflow assets
- `docs/`: Project docs and architecture notes

## Quick Start

### 1. Database

Use Docker Compose to start PostgreSQL:

```bash
docker compose -f docker/docker-compose.yml up postgres -d
```

Default database connection:

```bash
postgresql+psycopg://app:app@localhost:5432/restaurant_decision
```

### 2. Backend

Install dependencies:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip
backend/.venv/bin/pip install -e ./backend[dev]
```

Start the FastAPI server:

```bash
cp .env.example .env
backend/.venv/bin/uvicorn app.main:app --app-dir backend/src --reload --host 0.0.0.0 --port 8000
```

Backend default URL: `http://localhost:8000`

Default CORS origins:

```bash
http://127.0.0.1:3000,http://localhost:3000
```

### 3. Frontend

Requires Node.js 20+ and `npm`.

Install dependencies:

```bash
cd frontend
npm install
```

Start the Next.js app:

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 0.0.0.0 --port 3000
```

Frontend default URL: `http://localhost:3000`

### Full Stack via Docker

```bash
make docker-up
```

## Notes

- The backend exposes health, restaurant data, and chat endpoints.
- The frontend is still a shell; restaurant-specific business workflows are intentionally deferred.
- The current chat runtime is provider-pluggable and defaults to a local `stub` provider for development and tests.
