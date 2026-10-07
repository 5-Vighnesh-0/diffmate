from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from app.api import health, webhooks
from app.core.config import get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.db = create_async_engine(settings.database_url, pool_pre_ping=True)
    # One arq pool serves as the job queue and as the plain Redis client.
    app.state.redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.redis.aclose()
    await app.state.db.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="DiffMate", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(health.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
