import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Throwaway test database only (docker run ... -p 127.0.0.1:55432:5432), never the dev DB.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:test@localhost:55432/postgres"
)
BACKEND = Path(__file__).resolve().parents[2]


def alembic(*args: str) -> None:
    env = {"PATH": os.environ["PATH"], "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, check=True
    )


@pytest.fixture
async def sessionmaker():
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("test Postgres not running on 127.0.0.1:55432")
    alembic("upgrade", "head")
    yield async_sessionmaker(engine, expire_on_commit=False)
    alembic("downgrade", "base")
    await engine.dispose()


@pytest.fixture
async def session(sessionmaker):
    async with sessionmaker() as s:
        yield s
