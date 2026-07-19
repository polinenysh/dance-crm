import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.session import SessionDep, engine
from app.modules.router import api_router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Application started name=%s version=%s", settings.app_name, settings.app_version)
    yield
    logger.info("Application stopped")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CRM-система для сети школ танцев",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database", tags=["System"])
async def database_health_check(session: SessionDep) -> dict[str, str]:
    """Проверяет доступность базы данных."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "available"}
