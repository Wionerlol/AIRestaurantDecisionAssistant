from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_restaurants import router as restaurants_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(health_router)
app.include_router(restaurants_router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "message": "Backend skeleton is running.",
    }
