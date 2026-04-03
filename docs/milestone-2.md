# Milestone 2

## Goal

- Bring up the data service.

## Delivered

### FastAPI project skeleton

The backend now includes:

- app startup lifecycle
- database initialization on startup
- database-backed restaurant endpoints

Key files:

- [main.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/main.py)
- [routes_restaurants.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/api/routes_restaurants.py)

### PostgreSQL schema

Application schema is defined in two places:

- SQLAlchemy models:
  - [models.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/db/models.py)
- SQL reference:
  - [postgres_schema.sql](/home/louis/projects/AIRestaurantDecisionAssistant/sql/postgres_schema.sql)

### Tables

Implemented tables:

- `restaurants`
- `reviews`
- `restaurant_aspect_signals`

`restaurant_aspect_signals` is intentionally a placeholder precompute table for the next milestone. It already exists in the database and is seeded with baseline rows keyed by restaurant ID.

### Basic endpoints

Implemented and database-backed:

- `GET /restaurants/{business_id}`
- `GET /restaurants/{business_id}/reviews`

Also retained:

- `GET /restaurants`
- `GET /health`

### Local startup via Docker Compose

Compose file:

- [docker-compose.yml](/home/louis/projects/AIRestaurantDecisionAssistant/docker/docker-compose.yml)

Services:

- `postgres`
- `backend`
- `frontend`

Backend startup behavior:

1. connect to PostgreSQL
2. create schema if missing
3. seed demo subset if tables are empty
4. expose API on port `8000`

## Done Condition Check

Done condition:

- Frontend or `curl` can retrieve restaurant details and review lists.

Status:

- Satisfied for backend and `curl`.

Example:

```bash
curl http://localhost:8000/restaurants/_ab50qdWOk0DdB6XOrBitw
curl http://localhost:8000/restaurants/_ab50qdWOk0DdB6XOrBitw/reviews?limit=3
```

## Verification

Automated verification currently covers:

- schema bootstrap
- demo data seeding
- restaurant retrieval
- review retrieval

Test file:

- [test_restaurants.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/tests/test_restaurants.py)
