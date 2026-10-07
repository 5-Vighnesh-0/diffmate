import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.api.auth import STATE_COOKIE
from app.api.deps import get_http
from app.core.sessions import SESSION_COOKIE, SESSION_TTL_SECONDS


@pytest.fixture
def github(app):
    """Fake github.com + api.github.com for the OAuth exchange and user lookups."""
    calls = {"token_form": None, "fail_token": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            calls["token_form"] = parse_qs(request.content.decode())
            if calls["fail_token"]:
                return httpx.Response(200, json={"error": "bad_verification_code"})
            return httpx.Response(200, json={"access_token": "user-token-secret"})
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": 7, "login": "vighnesh"})
        if request.url.path == "/user/installations":
            if calls.get("broken_user_api"):
                return httpx.Response(502, text="<html>bad gateway</html>")
            return httpx.Response(200, json={"installations": [{"id": 42}, {"id": 43}]})
        if request.url.path == "/user/installations/42/repositories":
            return httpx.Response(200, json={"repositories": [{"id": 1}, {"id": 2}]})
        if request.url.path == "/user/installations/43/repositories":
            return httpx.Response(200, json={"repositories": [{"id": 9}]})
        return httpx.Response(404)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_http] = lambda: http
    return calls


async def start_login(client) -> tuple[str, dict]:
    r = await client.get("/auth/login")
    assert r.status_code == 302
    query = parse_qs(urlparse(r.headers["location"]).query)
    client.cookies.set(STATE_COOKIE, r.cookies[STATE_COOKIE])
    return query["state"][0], query


async def test_login_redirects_to_github_with_state_and_s256_pkce(client, redis):
    state, query = await start_login(client)

    verifier = redis.data[f"oauth:{state}"]
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    assert query["code_challenge"] == [expected.decode()]
    assert query["code_challenge_method"] == ["S256"]
    assert redis.ttl[f"oauth:{state}"] == 600
    assert len(state) >= 32 and 43 <= len(verifier) <= 128


async def test_callback_with_unknown_state_is_rejected(client, redis, github):
    r = await client.get("/auth/callback", params={"code": "c", "state": "forged"})

    assert r.status_code == 400
    assert github["token_form"] is None


async def test_state_is_single_use(client, redis, github):
    state, _ = await start_login(client)
    first = await client.get("/auth/callback", params={"code": "c", "state": state})
    second = await client.get("/auth/callback", params={"code": "c", "state": state})

    assert first.status_code == 302
    assert second.status_code == 400


async def test_callback_creates_a_safe_session_and_stores_no_github_token(client, redis, github):
    state, _ = await start_login(client)
    verifier = redis.data[f"oauth:{state}"]

    r = await client.get("/auth/callback", params={"code": "c", "state": state})

    assert r.status_code == 302
    assert r.headers["location"] == "http://localhost:5173/dashboard"
    assert github["token_form"]["code_verifier"] == [verifier]
    cookie = r.headers["set-cookie"].lower()
    for flag in ("httponly", "secure", "samesite=lax", f"max-age={SESSION_TTL_SECONDS}", "path=/"):
        assert flag in cookie
    sessions = {k: json.loads(v) for k, v in redis.data.items() if k.startswith("session:")}
    assert [(s["login"], s["installation_ids"], s["repo_ids"]) for s in sessions.values()] == [
        ("vighnesh", [42, 43], [1, 2, 9])
    ]
    assert redis.ttl[next(iter(sessions))] == 8 * 3600
    assert not any("user-token-secret" in v for v in redis.data.values())


async def test_failed_token_exchange_creates_no_session(client, redis, github):
    github["fail_token"] = True
    state, _ = await start_login(client)

    r = await client.get("/auth/callback", params={"code": "c", "state": state})

    assert r.status_code == 400
    assert not any(k.startswith("session:") for k in redis.data)


async def login(client, redis, github) -> str:
    state, _ = await start_login(client)
    r = await client.get("/auth/callback", params={"code": "c", "state": state})
    client.cookies.set(SESSION_COOKIE, r.cookies[SESSION_COOKIE])
    me = await client.get("/api/me")
    return me.json()["csrf_token"]


async def test_me_requires_a_session(client, redis):
    assert (await client.get("/api/me")).status_code == 401


async def test_me_returns_user_installations_and_quota(client, redis, github):
    await login(client, redis, github)

    me = (await client.get("/api/me")).json()

    assert me["user"] == {"id": 7, "login": "vighnesh"}
    assert me["installations"] == [42, 43]
    assert me["llm"] == {"requests_today": 0, "daily_cap": 0}
    assert len(me["csrf_token"]) >= 32


async def test_logout_needs_csrf_then_ends_the_session(client, redis, github):
    csrf = await login(client, redis, github)

    denied = await client.post("/auth/logout")
    ok = await client.post("/auth/logout", headers={"X-CSRF-Token": csrf})

    assert denied.status_code == 403
    assert ok.status_code == 204
    assert not any(k.startswith("session:") for k in redis.data)
    assert (await client.get("/api/me")).status_code == 401


async def test_login_state_is_bound_to_the_browser_that_started_it(client, redis, github):
    # Login CSRF: the attacker starts a login, then sends the victim the callback link.
    state, _ = await start_login(client)
    client.cookies.clear()  # the victim's browser never received the state cookie

    r = await client.get("/auth/callback", params={"code": "attacker-code", "state": state})

    assert r.status_code == 400
    assert github["token_form"] is None


async def test_state_cookie_is_httponly_short_lived_and_scoped(client, redis):
    r = await client.get("/auth/login")

    cookie = r.headers["set-cookie"].lower()
    for flag in ("httponly", "secure", "samesite=lax", "max-age=600", "path=/auth"):
        assert flag in cookie


async def test_github_errors_during_login_give_a_clean_502(client, redis, github):
    github["broken_user_api"] = True
    state, _ = await start_login(client)

    r = await client.get("/auth/callback", params={"code": "c", "state": state})

    assert r.status_code == 502
    assert r.json() == {"error": {"code": "bad_gateway", "message": "GitHub login failed"}}
    assert not any(k.startswith("session:") for k in redis.data)


async def test_denied_authorization_is_a_400_without_echoing_input(client, redis, github):
    r = await client.get("/auth/callback", params={"error": "access_denied", "state": "<x>"})

    assert r.status_code == 400
    assert "<x>" not in r.text
    assert r.json()["error"]["code"] == "bad_request"


async def test_logout_with_an_expired_session_still_clears_the_cookie(client, redis):
    client.cookies.set(SESSION_COOKIE, "expired-session-id")

    r = await client.post("/auth/logout")

    assert r.status_code == 204
    assert SESSION_COOKIE in r.headers.get("set-cookie", "")


async def test_unknown_routes_use_the_standard_error_shape(client, redis):
    r = await client.get("/nope")

    assert r.json() == {"error": {"code": "not_found", "message": "Not Found"}}
