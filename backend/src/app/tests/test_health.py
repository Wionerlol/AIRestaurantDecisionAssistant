from fastapi.middleware.cors import CORSMiddleware

from app.main import app
from app.api.routes_health import healthcheck


def test_healthcheck() -> None:
    assert healthcheck() == {"status": "ok"}


def test_cors_middleware_is_configured() -> None:
    assert any(middleware.cls is CORSMiddleware for middleware in app.user_middleware)
