PYTHON ?= python3
VENV ?= .venv
BACKEND_VENV := backend/$(VENV)
NPM ?= npm
DOCKER_COMPOSE ?= docker compose -f docker/docker-compose.yml
BACKEND_HOST ?= 0.0.0.0
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: backend-install backend-dev backend-test frontend-install frontend-dev docker-up docker-down fmt

backend-install:
	$(PYTHON) -m venv $(BACKEND_VENV)
	$(BACKEND_VENV)/bin/pip install --upgrade pip
	$(BACKEND_VENV)/bin/pip install -e ./backend[dev]

backend-dev:
	$(BACKEND_VENV)/bin/uvicorn app.main:app --app-dir backend/src --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

backend-test:
	$(BACKEND_VENV)/bin/pytest backend/src/app/tests

frontend-install:
	cd frontend && $(NPM) install

frontend-dev:
	cd frontend && $(NPM) run dev -- --hostname 0.0.0.0 --port $(FRONTEND_PORT)

docker-up:
	$(DOCKER_COMPOSE) up --build

docker-down:
	$(DOCKER_COMPOSE) down

fmt:
	$(BACKEND_VENV)/bin/ruff format backend/src
