# AI Restaurant Decision Assistant

Monorepo skeleton for an AI restaurant review analysis assistant. This repository is intentionally minimal: the backend and frontend both start independently, while business logic is deferred to later milestones.

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

- The backend exposes a health endpoint and a root metadata endpoint.
- The frontend is a static shell wired to the planned monorepo structure.
- LangGraph, tools, memory, and business workflows are not implemented in this initialization step.

