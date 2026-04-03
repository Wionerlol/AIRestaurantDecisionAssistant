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

### Backend

```bash
make backend-install
make backend-dev
```

Backend default URL: `http://localhost:8000`

### Frontend

Requires Node.js 20+ and `npm` or `pnpm`.

```bash
make frontend-install
make frontend-dev
```

Frontend default URL: `http://localhost:3000`

### Docker

```bash
make docker-up
```

## Notes

- The backend exposes health, restaurant data, and chat endpoints.
- The frontend is still a shell; restaurant-specific business workflows are intentionally deferred.
- The current chat runtime is provider-pluggable and defaults to a local `stub` provider for development and tests.
