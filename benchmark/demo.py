"""Record the real DiffMate reviews shown on the landing page (frontend/src/lib/demo.json).

    cd backend && PYTHONPATH=.. uv run python -m benchmark.demo

Runs the real agent offline (no GitHub) on one example file: once as a new file with a bug
(the scroll-typing scene), and once per "plant a bug" choice. Uses the worker's free-tier
model and its shared daily cap. The page shows exactly what was recorded, with the date."""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from redis.asyncio import Redis

from app.agent.budget import DailyCap
from app.agent.filters import filter_findings
from app.agent.llm import GeminiLLM
from app.core.config import get_settings
from benchmark.runner import review

OUT = Path(__file__).parent.parent / "frontend" / "src" / "lib" / "demo.json"
PATH = "stats.py"

CLEAN = """import subprocess


def average(values):
    if not values:
        return 0.0
    total = 0
    for v in values:
        total += v
    return total / len(values)


def last_n(items, n):
    return items[len(items) - n :]


def archive(path):
    subprocess.run(["tar", "-czf", path + ".tgz", path], check=True)
"""

# Each break replaces one line of CLEAN. Keys are what the visitor picks.
BREAKS = {
    "loop": (
        "    for v in values:\n        total += v\n",
        "    for i in range(1, len(values)):\n        total += values[i]\n",
    ),
    "slice": ("    return items[len(items) - n :]\n", "    return items[-n:]\n"),
    "shell": (
        '    subprocess.run(["tar", "-czf", path + ".tgz", path], check=True)\n',
        '    subprocess.run(f"tar -czf {path}.tgz {path}", shell=True)\n',
    ),
}


def broken(name: str) -> str:
    old, new = BREAKS[name]
    if old not in CLEAN:
        raise ValueError(f"break {name!r} does not match the clean file")
    return CLEAN.replace(old, new)


async def record(case: dict, llm, cap) -> dict:
    files, _, result, _, seconds = await review(case, llm, cap)
    settings = get_settings()
    statuses = filter_findings(
        result.findings,
        {f.path: f.lines for f in files},
        settings.confidence_threshold,
        settings.comment_cap,
    )
    return {
        "after": case["after"][PATH],
        "comments": [f.model_dump() for f, status in statuses if status == "posted"],
        "trace": [t.summary for t in result.trace],
        "stop_reason": result.stop_reason,
        "llm_requests": result.llm_requests,
        "seconds": round(seconds, 1),
    }


async def main() -> int:
    settings = get_settings()
    key = settings.gemini_api_key.get_secret_value()
    if not key:
        print("GEMINI_API_KEY is not set in .env", file=sys.stderr)
        return 2
    llm = GeminiLLM(
        key, settings.llm_model, settings.llm_thinking_level, settings.llm_timeout_seconds
    )
    redis = Redis.from_url(settings.redis_url)
    cap = DailyCap(
        redis,
        settings.llm_daily_request_cap,
        settings.llm_requests_per_minute,
        model=settings.llm_model,
    )
    title, body = "Add stats helpers", "Small helpers for averages, recent items, and backups."

    out = {
        "model": settings.llm_model,
        "recorded": datetime.now(UTC).strftime("%Y-%m-%d"),
        "path": PATH,
        "clean": CLEAN,
    }
    out["peak"] = await record(
        {"title": title, "body": body, "before": {}, "after": {PATH: broken("loop")}}, llm, cap
    )
    out["breaks"] = {}
    for name in BREAKS:
        case = {
            "title": title,
            "body": body,
            "before": {PATH: CLEAN},
            "after": {PATH: broken(name)},
        }
        out["breaks"][name] = await record(case, llm, cap)
    await redis.aclose()

    bad = [
        k
        for k, v in [("peak", out["peak"]), *out["breaks"].items()]
        if v["stop_reason"] != "submitted"
    ]
    if bad:  # never ship a page built on a run that did not finish
        print(f"runs did not finish: {bad}; nothing written", file=sys.stderr)
        return 3
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for k, v in [("peak", out["peak"]), *out["breaks"].items()]:
        print(
            k, [(c["line"], c["explanation"][:70]) for c in v["comments"]], v["llm_requests"], "req"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
