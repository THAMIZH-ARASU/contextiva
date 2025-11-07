from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from src.shared.config.logging import configure_logging
from src.shared.infrastructure.database.connection import init_pool, close_pool, ping
from src.api.middleware.logging_middleware import logging_middleware
from src.api.v1.routes import auth, projects


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(logging.INFO)
    await init_pool()
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="Contextiva API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
app.middleware("http")(logging_middleware)

# Register routers
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])


@app.get("/api/v1/health")
async def health() -> dict:
    db_ok = await ping()
    return {"status": "ok", "db": "ok" if db_ok else "down"}


