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

The project uses SQLite for the current stage. PostgreSQL / `pgvector` is not required because the current system is database-backed structured retrieval, not RAG.

Default local database connection:

```bash
sqlite:///./backend/data/app.db
```

The backend creates tables and seeds data on startup when `DATABASE_AUTO_SEED=true`. The working data files live under `backend/data/`, which is ignored by Git because the expanded local dataset is large.

To rebuild the local restaurant/review sample from the Yelp academic dataset:

```bash
python3 scripts/build_sample_dataset.py
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
export DATABASE_URL=sqlite:///./backend/data/app.db
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

Docker Compose also uses SQLite and bind-mounts `backend/data` into the backend container. It does not start PostgreSQL.

## Notes

- The backend exposes health, restaurant data, and chat endpoints.
- The frontend is still a shell; restaurant-specific business workflows are intentionally deferred.
- The current chat runtime is provider-pluggable and defaults to a local `stub` provider for development and tests.
- SQLite is the expected database for this phase; PostgreSQL and vector search can be reconsidered only if RAG or embedding search becomes necessary later.
