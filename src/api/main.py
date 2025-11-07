from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from src.infrastructure.external.llm import ProviderFactory
from src.shared.config.logging import configure_logging
from src.shared.infrastructure.database.connection import init_pool, close_pool, ping
from src.api.middleware.logging_middleware import logging_middleware
from src.api.v1.routes import auth, projects


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown tasks:
    - Initialize logging
    - Initialize database connection pool
    - Initialize LLM providers (lazy initialization via factory)
    - Clean up resources on shutdown
    """
    configure_logging(logging.INFO)
    await init_pool()
    
    # Note: LLM providers are initialized lazily via ProviderFactory
    # on first use. We just log that they're available.
    logging.info("LLM provider factory ready (providers will be initialized on first use)")
    
    try:
        yield
    finally:
        # Close all provider instances and release resources
        await ProviderFactory.close_all()
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


