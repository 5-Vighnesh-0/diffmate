import os

import pytest
from arq import create_pool
from arq.connections import RedisSettings

from app.queue.jobs import enqueue_review

# Separate DB number so this test never touches dev data.
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
async def pool():
    try:
        p = await create_pool(RedisSettings.from_dsn(TEST_REDIS_URL), retry=0)
    except Exception:
        pytest.skip("Redis not running; start it with: docker compose up -d redis")
    await p.flushdb()
    yield p
    await p.flushdb()
    await p.aclose()


async def test_real_arq_queues_a_commit_only_once(pool):
    first = await enqueue_review(pool, repo="o/r", pr=7, sha="a" * 40, installation_id=1)
    again = await enqueue_review(pool, repo="o/r", pr=7, sha="a" * 40, installation_id=1)
    next_commit = await enqueue_review(pool, repo="o/r", pr=7, sha="b" * 40, installation_id=1)

    assert (first, again, next_commit) == (True, False, True)
