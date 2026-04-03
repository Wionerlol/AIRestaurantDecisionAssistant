# Backend

Python 3.12 FastAPI service backed by SQLAlchemy and PostgreSQL.

Current endpoints:

- `GET /health`
- `GET /`
- `GET /restaurants`
- `GET /restaurants/{business_id}`
- `GET /restaurants/{business_id}/reviews`
- `POST /chat`

## Local Run

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .[dev]
.venv/bin/uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

Default local database URL:

```bash
sqlite:///./backend/data/app.db
```

To use PostgreSQL locally:

```bash
export DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/restaurant_decision
```

To use OpenAI for chat:

```bash
export LLM_PROVIDER=openai
export LLM_MODEL_NAME=gpt-4o-mini
export OPENAI_API_KEY=your_api_key
```

## Docker Compose

From repository root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

The backend will create tables and seed demo data on startup when `DATABASE_AUTO_SEED=true`.

For local development and tests, chat defaults to the `stub` provider so no external LLM key is required.
