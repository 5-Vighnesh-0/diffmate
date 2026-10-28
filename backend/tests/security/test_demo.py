"""Plant a bug for real: a visitor opens a real PR in the sandbox repo, from a fixed example."""

import json

import httpx
import pytest

from app.api.deps import get_http, get_redis
from app.core.config import Settings, get_settings
from tests.conftest import FakeRedis

SANDBOX = "me/diffmate-sandbox"


class FakeSandbox:
    """The sandbox repo on GitHub, as far as the demo touches it."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None]] = []
        self.open_prs = [
            {"number": 3, "head": {"ref": "demo-old"}, "created_at": "2026-01-01T00:00:00Z"}
        ]

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        path, method = request.url.path, request.method
        self.calls.append((method, path, body))
        assert request.headers["authorization"] == "Bearer sandbox-token"
        base = f"/repos/{SANDBOX}"
        if path == f"{base}/pulls" and method == "GET":
            return httpx.Response(200, json=self.open_prs)
        if path == f"{base}/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "m" * 40}})
        if path == f"{base}/git/refs" and method == "POST":
            return httpx.Response(201, json={})
        if path == f"{base}/contents/stats.py" and method == "GET":
            return httpx.Response(200, json={"sha": "f" * 40})
        if path == f"{base}/contents/stats.py" and method == "PUT":
            return httpx.Response(200, json={})
        if path == f"{base}/pulls" and method == "POST":
            return httpx.Response(
                201, json={"number": 12, "html_url": f"https://github.com/{SANDBOX}/pull/12"}
            )
        if path.startswith(f"{base}/pulls/") and method == "PATCH":
            return httpx.Response(200, json={})
        if path.startswith(f"{base}/git/refs/heads/") and method == "DELETE":
            return httpx.Response(204)
        if path == f"{base}/pulls/12/comments":
            return httpx.Response(
                200,
                json=[
                    {"user": {"type": "User"}, "line": 8, "body": "me"},
                    {"user": {"type": "Bot"}, "line": 8, "body": "**Bug** · high severity"},
                ],
            )
        return httpx.Response(404, json={})


@pytest.fixture
def sandbox(app):
    fake = FakeSandbox()
    redis = FakeRedis()
    settings = Settings(
        database_url="postgresql+asyncpg://x/y",
        redis_url="redis://x",
        demo_repo=SANDBOX,
        demo_token="sandbox-token",
        demo_daily_cap=2,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_http] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(fake.handler), base_url="https://api.github.com"
    )
    return fake


async def test_the_demo_is_off_until_a_sandbox_is_configured(client, app):
    app.dependency_overrides[get_redis] = lambda: FakeRedis()
    app.dependency_overrides[get_http] = lambda: None  # never reached

    assert (await client.get("/api/demo")).json() == {"enabled": False}
    assert (await client.post("/api/demo", json={"example": "loop"})).status_code == 404


async def test_a_visitor_opens_a_real_pr_with_the_recorded_change(client, sandbox):
    assert (await client.get("/api/demo")).json() == {"enabled": True}

    r = await client.post("/api/demo", json={"example": "loop"})

    assert r.status_code == 201
    assert r.json() == {"pr": 12, "url": f"https://github.com/{SANDBOX}/pull/12"}
    put = next(b for m, p, b in sandbox.calls if m == "PUT")
    import base64

    from app.api.demo import examples

    assert base64.b64decode(put["content"]).decode() == examples()["loop"]
    # an old demo PR was closed and its branch deleted
    assert ("PATCH", f"/repos/{SANDBOX}/pulls/3", {"state": "closed"}) in sandbox.calls
    assert ("DELETE", f"/repos/{SANDBOX}/git/refs/heads/demo-old", None) in sandbox.calls


async def test_only_the_fixed_examples_can_be_planted(client, sandbox):
    for body in [{"example": "rm -rf"}, {"example": "loop", "content": "anything"}, {}]:
        assert (await client.post("/api/demo", json=body)).status_code == 422
    assert not [c for c in sandbox.calls if c[0] == "PUT"]


async def test_the_demo_stops_at_its_daily_cap(client, sandbox):
    assert (await client.post("/api/demo", json={"example": "loop"})).status_code == 201
    assert (await client.post("/api/demo", json={"example": "slice"})).status_code == 201
    r = await client.post("/api/demo", json={"example": "shell"})

    assert r.status_code == 429
    assert "today" in r.text


async def test_status_shows_only_diffmates_comments(client, sandbox):
    r = await client.get("/api/demo/12")

    assert r.json() == {
        "reviewed": True,
        "url": f"https://github.com/{SANDBOX}/pull/12",
        "comments": [{"line": 8, "body": "**Bug** · high severity"}],
    }
