from app.api.health import health_checks


async def test_health_returns_ok_when_all_checks_pass(app, client, redis):
    app.dependency_overrides[health_checks] = lambda: {"redis": True}

    r = await client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_health_returns_503_naming_the_failing_check(app, client, redis):
    app.dependency_overrides[health_checks] = lambda: {"redis": False}

    r = await client.get("/health")

    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "checks": {"redis": False}}


async def test_health_checks_time_out_instead_of_hanging(monkeypatch):
    import asyncio
    import time
    from types import SimpleNamespace

    from app.api import health

    class StuckRedis:
        async def ping(self):
            await asyncio.sleep(10)

    class Db:
        def connect(self):
            raise AssertionError("/health must not touch Postgres")

    monkeypatch.setattr(health, "CHECK_TIMEOUT_SECONDS", 0.1)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(db=Db(), redis=StuckRedis()))
    )

    start = time.monotonic()
    checks = await health.health_checks(request)

    assert checks == {"redis": False}
    assert time.monotonic() - start < 1
