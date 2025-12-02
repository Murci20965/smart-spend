# 1. Import FastAPI
import logging

from arq import create_pool
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import configure_logging
from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.routers.transactions import router as transactions_router
from app.routers.upload import router as upload_router

from contextlib import asynccontextmanager

# Configure logging early
configure_logging()

# Configure a module-level logger
logger = logging.getLogger("smart_spend")


@asynccontextmanager
async def lifespan(app):
    """Lifespan context: create and teardown app resources (Redis pool).

    Using a lifespan handler avoids FastAPI's deprecated on_event hooks.
    """
    from app.core.config import settings

    try:
        import sys

        if getattr(settings, "ENV", "development") == "testing" or "pytest" in sys.modules:
            logger.info("Skipping Redis pool creation in testing environment")
            app.state.redis_pool = None
        else:
            logger.info("Creating Redis pool on startup")
            app.state.redis_pool = await create_pool(settings.REDIS_SETTINGS)
        yield
    finally:
        pool = getattr(app.state, "redis_pool", None)
        if pool:
            try:
                await pool.close()
            except Exception:
                logger.exception("Error closing Redis pool during shutdown")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db": result.scalar()}


# -----------------------------
# REGISTER ROUTERS
# -----------------------------
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(transactions_router)
