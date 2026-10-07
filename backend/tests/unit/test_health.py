from app.api.health import health_checks


async def test_health_returns_ok_when_all_checks_pass(app, client):
    app.dependency_overrides[health_checks] = lambda: {"postgres": True, "redis": True}

    r = await client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_health_returns_503_naming_the_failing_check(app, client):
    app.dependency_overrides[health_checks] = lambda: {"postgres": True, "redis": False}

    r = await client.get("/health")

    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "checks": {"postgres": True, "redis": False}}


async def test_health_checks_time_out_instead_of_hanging(monkeypatch):
    import asyncio
    import time
    from types import SimpleNamespace

    from app.api import health

    class StuckRedis:
        async def ping(self):
            await asyncio.sleep(10)

    class DeadDb:
        def connect(self):
            raise ConnectionError("down")

    monkeypatch.setattr(health, "CHECK_TIMEOUT_SECONDS", 0.1)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(db=DeadDb(), redis=StuckRedis()))
    )

    start = time.monotonic()
    checks = await health.health_checks(request)

    assert checks == {"postgres": False, "redis": False}
    assert time.monotonic() - start < 1
