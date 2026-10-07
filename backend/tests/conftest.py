import os

# Fake, test-only values; set before the app reads settings. Never real secrets.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret"

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.core.config import Settings  # noqa: E402

# Never let tests read the real ../.env (it holds real secrets).
Settings.model_config["env_file"] = None

from app.main import create_app  # noqa: E402


@pytest.fixture
def app():
    # ASGITransport does not run the lifespan, so no real Postgres/Redis connection is opened.
    return create_app()


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
