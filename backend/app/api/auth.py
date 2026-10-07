"""Dashboard login through the GitHub App's user OAuth flow, with state and PKCE (S256)."""

import base64
import hashlib
import hmac
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.agent.budget import daily_key
from app.api.deps import get_http, get_redis, get_session
from app.core.config import Settings, get_settings
from app.core.sessions import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    Session,
    create_session,
    delete_session,
    load_session,
)

router = APIRouter()
log = logging.getLogger(__name__)

STATE_TTL_SECONDS = 600
STATE_COOKIE = "diffmate_oauth_state"
MAX_REPOS_PER_INSTALLATION = 100


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@router.get("/auth/login")
async def login(settings: Settings = Depends(get_settings), redis=Depends(get_redis)):
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)  # 86 chars, within PKCE's 43-128
    await redis.set(f"oauth:{state}", verifier, ex=STATE_TTL_SECONDS)
    query = urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": f"{settings.public_api_url}/auth/callback",
            "state": state,
            "code_challenge": _challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    response = RedirectResponse(
        f"https://github.com/login/oauth/authorize?{query}", status_code=302
    )
    # Binds the login to this browser: a callback link sent by someone else carries their
    # state, which won't match this cookie (login CSRF).
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth",
    )
    return response


async def _github_identity(http, settings: Settings, code: str, verifier: str):
    """Code -> user token -> (user, installations, repos). The token is dropped afterwards."""
    r = await http.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_oauth_client_id,
            "client_secret": settings.github_oauth_client_secret.get_secret_value(),
            "code": code,
            "redirect_uri": f"{settings.public_api_url}/auth/callback",
            "code_verifier": verifier,
        },
    )
    try:
        answer = r.json()
    except ValueError:
        answer = {}
    token = answer.get("access_token") if r.status_code == 200 else None
    if not token:
        # GitHub's error code is not secret (e.g. "incorrect_client_credentials"); log it.
        log.warning(
            "login failed: token exchange HTTP %s, error=%s",
            r.status_code,
            str(answer.get("error", "none"))[:60],
        )
        raise HTTPException(400, "GitHub login failed")
    auth = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    async def get(url: str) -> dict:
        resp = await http.get(url, params={"per_page": 100}, headers=auth)
        resp.raise_for_status()
        return resp.json()

    try:
        user = await get("https://api.github.com/user")
        found = await get("https://api.github.com/user/installations")
        installation_ids = [int(i["id"]) for i in found["installations"]]
        repo_ids: list[int] = []
        for inst in installation_ids:
            # Membership in an org installation does not mean access to all of its repos:
            # keep only the repos GitHub says this user can reach.
            repos = await get(f"https://api.github.com/user/installations/{inst}/repositories")
            repo_ids += [int(r["id"]) for r in repos["repositories"][:MAX_REPOS_PER_INSTALLATION]]
        return int(user["id"]), str(user["login"]), installation_ids, repo_ids
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        log.warning("login failed: GitHub lookup error %s", type(e).__name__)
        raise HTTPException(502, "GitHub login failed") from e


@router.get("/auth/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    settings: Settings = Depends(get_settings),
    redis=Depends(get_redis),
    http=Depends(get_http),
):
    browser_state = request.cookies.get(STATE_COOKIE, "")
    if not code or not state or not hmac.compare_digest(browser_state, state):
        log.warning("login rejected: missing code or state not from this browser")
        raise HTTPException(400, "Login expired or was started elsewhere, please try again")
    stored = await redis.getdel(f"oauth:{state[:100]}")  # one-time: replays find nothing
    # Real Redis returns bytes; sending b"..." would break PKCE (GitHub: invalid_grant).
    verifier = stored.decode() if isinstance(stored, bytes) else stored
    if not verifier:
        log.warning("login rejected: unknown or reused state")
        raise HTTPException(400, "Login expired, please try again")

    user_id, login, installation_ids, repo_ids = await _github_identity(
        http, settings, code, verifier
    )
    sid, _ = await create_session(redis, user_id, login, installation_ids, repo_ids)
    log.info("login %s (%d installations, %d repos)", login, len(installation_ids), len(repo_ids))
    response = RedirectResponse(f"{settings.frontend_origin}/dashboard", status_code=302)
    response.delete_cookie(STATE_COOKIE, path="/auth", secure=True, httponly=True, samesite="lax")
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, redis=Depends(get_redis)):
    sid = request.cookies.get(SESSION_COOKIE, "")
    session = await load_session(redis, sid)
    if session is not None:
        token = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(token.encode(), session.csrf.encode()):
            raise HTTPException(403, "Missing or wrong CSRF token")
        await delete_session(redis, sid)
        log.info("logout %s", session.login)
    # An expired session has nothing to protect: just clear the stale cookie.
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.get("/api/me")
async def me(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    redis=Depends(get_redis),
):
    used = await redis.get(daily_key(settings.llm_model))
    return {
        "user": {"id": session.user_id, "login": session.login},
        "installations": session.installation_ids,
        "csrf_token": session.csrf,
        "llm": {
            "requests_today": min(int(used or 0), settings.llm_daily_request_cap),
            "daily_cap": settings.llm_daily_request_cap,
        },
    }
