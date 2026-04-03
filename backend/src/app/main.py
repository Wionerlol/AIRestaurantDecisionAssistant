from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_restaurants import router as restaurants_router
from app.core.config import settings
from app.db.bootstrap import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=settings.app_docs_url,
    redoc_url=settings.app_redoc_url,
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(restaurants_router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "message": "Backend skeleton is running.",
    }
