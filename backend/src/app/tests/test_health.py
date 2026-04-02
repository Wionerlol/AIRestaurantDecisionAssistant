from app.api.routes_health import healthcheck


def test_healthcheck() -> None:
    assert healthcheck() == {"status": "ok"}
