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


class FakeRedis:
    """In-memory stand-in for the Redis calls the API makes (TTL recorded, not enforced)."""

    def __init__(self):
        self.data: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        if ex:
            self.ttl[key] = ex
        return True

    async def get(self, key):
        return self.data.get(key)

    async def getdel(self, key):
        return self.data.pop(key, None)

    async def delete(self, key):
        self.data.pop(key, None)

    async def incr(self, key):
        self.data[key] = str(int(self.data.get(key, "0")) + 1)
        return int(self.data[key])

    async def expire(self, key, seconds):
        self.ttl[key] = seconds


@pytest.fixture
def redis(app):
    from app.api.deps import get_redis

    fake = FakeRedis()
    app.dependency_overrides[get_redis] = lambda: fake
    return fake
