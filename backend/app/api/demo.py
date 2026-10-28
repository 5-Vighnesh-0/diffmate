"""Plant a bug for real: a visitor picks one of the landing page's recorded examples and the
API opens a real pull request with that change in a public sandbox repo, where DiffMate
reviews it like any other. Visitors never send code or text: only an example's name.

The sandbox token is a fine-grained token for that one repo (contents and pull requests:
write). DiffMate's own GitHub App stays read-only."""

import base64
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_http, get_redis
from app.core.config import Settings, get_settings
from app.core.ratelimit import rate_limit

router = APIRouter()
log = logging.getLogger(__name__)

TITLES = {
    "loop": "Use an index in average",
    "slice": "Shorten last_n with a slice",
    "shell": "Simplify archive",
}
STALE = timedelta(minutes=30)  # older demo PRs are closed when a new one opens


@cache
def examples() -> dict[str, str]:
    """The recorded examples' changed stats.py, from the landing page's own data file."""
    data = json.loads(Path(get_settings().demo_examples_file).read_text())
    return {key: data["breaks"][key]["after"] for key in TITLES} | {"clean": data["clean"]}


class DemoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    example: Literal["loop", "slice", "shell"]


def _sandbox(settings: Settings) -> tuple[str, dict]:
    token = settings.demo_token.get_secret_value()
    if not settings.demo_repo or not token:
        raise HTTPException(404, "The live demo is not set up")
    # Full URLs: the API's shared client (app.state.http) has no base URL.
    return f"https://api.github.com/repos/{settings.demo_repo}", {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _close_stale(http, base: str, auth: dict) -> None:
    """Close demo PRs older than 30 minutes and delete their branches (best effort)."""
    r = await http.get(f"{base}/pulls", params={"state": "open", "per_page": 50}, headers=auth)
    r.raise_for_status()
    for pr in r.json():
        ref = pr["head"]["ref"]
        opened = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        if ref.startswith("demo-") and datetime.now(UTC) - opened > STALE:
            await http.patch(f"{base}/pulls/{pr['number']}", json={"state": "closed"}, headers=auth)
            await http.delete(f"{base}/git/refs/heads/{ref}", headers=auth)


@router.get("/api/demo")
async def demo_status(settings: Settings = Depends(get_settings)):
    return {"enabled": bool(settings.demo_repo and settings.demo_token.get_secret_value())}


# 3 a minute per visitor on top of the router's limit; the daily cap bounds the AI quota.
@router.post("/api/demo", status_code=201, dependencies=[Depends(rate_limit("demo-plant", 3))])
async def plant(
    body: DemoIn,
    settings: Settings = Depends(get_settings),
    redis=Depends(get_redis),
    http=Depends(get_http),
):
    base, auth = _sandbox(settings)
    day = f"demo:{datetime.now(UTC):%Y-%m-%d}"
    used = await redis.get(day)
    if used is not None and int(used) >= settings.demo_daily_cap:
        raise HTTPException(429, "The live demo has run as often as it can today")
    branch = f"demo-{body.example}-{int(time.time())}"
    made_branch = False
    try:
        await _close_stale(http, base, auth)
        main = await http.get(f"{base}/git/ref/heads/main", headers=auth)
        main.raise_for_status()
        r = await http.post(
            f"{base}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": main.json()["object"]["sha"]},
            headers=auth,
        )
        r.raise_for_status()
        made_branch = True
        current = await http.get(f"{base}/contents/stats.py", params={"ref": branch}, headers=auth)
        change = {
            "message": TITLES[body.example],
            "content": base64.b64encode(examples()[body.example].encode()).decode(),
            "branch": branch,
        }
        if current.status_code == 200:
            change["sha"] = current.json()["sha"]
        r = await http.put(f"{base}/contents/stats.py", json=change, headers=auth)
        r.raise_for_status()
        pr = await http.post(
            f"{base}/pulls",
            json={
                "title": TITLES[body.example],
                "head": branch,
                "base": "main",
                "body": "Opened by a visitor of the DiffMate landing page (live demo).",
            },
            headers=auth,
        )
        pr.raise_for_status()
    except httpx.HTTPError as e:
        # Which call GitHub refused and why (path and status only; the token is never logged).
        req = getattr(e, "request", None)
        res = getattr(e, "response", None)
        log.warning(
            "demo: GitHub refused %s %s: %s %s",
            req.method if req else "?",
            req.url.path if req else "?",
            res.status_code if res is not None else type(e).__name__,
            res.text[:200] if res is not None else "",
        )
        if made_branch:  # don't leave a half-made demo branch behind
            await http.delete(f"{base}/git/refs/heads/{branch}", headers=auth)
        raise HTTPException(502, "GitHub could not open the demo pull request") from e
    # Only a demo that really opened counts against the day's limit.
    await redis.set(day, 0, nx=True, ex=2 * 24 * 3600)
    await redis.incr(day)
    return {"pr": pr.json()["number"], "url": pr.json()["html_url"]}


@router.get("/api/demo/{number}")
async def demo_review(
    number: int, settings: Settings = Depends(get_settings), http=Depends(get_http)
):
    """DiffMate's comments on a demo PR, once its review has landed (the page polls this)."""
    base, auth = _sandbox(settings)
    r = await http.get(f"{base}/pulls/{number}/comments", params={"per_page": 50}, headers=auth)
    if r.status_code == 404:
        raise HTTPException(404, "No such demo pull request")
    r.raise_for_status()
    comments = [
        {"line": c.get("line"), "body": c["body"]}
        for c in r.json()
        if (c.get("user") or {}).get("type") == "Bot"
    ]
    return {
        "reviewed": bool(comments),
        "url": f"https://github.com/{settings.demo_repo}/pull/{number}",
        "comments": comments,
    }
