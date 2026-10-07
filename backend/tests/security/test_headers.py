async def test_security_headers_on_every_response(client, redis, app):
    from app.api.health import health_checks

    app.dependency_overrides[health_checks] = lambda: {"postgres": True, "redis": True}

    r = await client.get("/health")

    assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "max-age=" in r.headers["strict-transport-security"]


async def test_cors_allows_only_the_frontend_origin(client, redis):
    def preflight(origin):
        return client.options(
            "/api/me",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )

    ok = await preflight("http://localhost:5173")
    evil = await preflight("https://evil.example")

    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert ok.headers["access-control-allow-credentials"] == "true"
    assert "access-control-allow-origin" not in evil.headers


async def test_webhook_rate_limit_is_120_per_minute_per_client_ip(client, redis):
    async def hit(ip):
        return await client.post(
            "/webhooks/github", content=b"{}", headers={"cf-connecting-ip": ip}
        )

    codes = [(await hit("203.0.113.9")).status_code for _ in range(121)]
    other_ip = await hit("198.51.100.1")

    assert codes[:120] == [401] * 120  # unsigned: rejected, but counted first
    assert codes[120] == 429
    assert other_ip.status_code == 401
    limited = await hit("203.0.113.9")
    assert int(limited.headers["retry-after"]) > 0
    assert all(redis.ttl.get(k) == 120 for k in redis.data if k.startswith("rl:"))


async def test_dashboard_rate_limit_is_60_per_minute(client, redis):
    codes = [(await client.get("/api/me")).status_code for _ in range(61)]

    assert codes[:60] == [401] * 60
    assert codes[60] == 429


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def fixed_minute(monkeypatch):
    # Keep all requests in one rate-limit window, however long the test takes.
    monkeypatch.setattr("app.core.ratelimit.now", lambda: 1_000_020.0)
