"""Run DiffMate on a slice of GitHub's ReviewBench (github.com/review-bench/ReviewBench, MIT).

    cd backend && PYTHONPATH=.. uv run python -m benchmark.reviewbench run --data DIR [--count 30]
    cd backend && PYTHONPATH=.. uv run python -m benchmark.reviewbench score

DIR is a local clone of the ReviewBench repo (data only). Each PR is checked out from its
review-bench mirror with git (hooks off, nothing in it runs) and reviewed exactly like the
worker does: linters, agent, the second look, the same filters. Results append to
benchmark/results/reviewbench-<model>.jsonl and resume like `bench`.

Scoring is an approximation of ReviewBench's grounded metrics: a note matches a golden
finding when it is in the same file and on or within 3 lines of its range. ReviewBench
itself matches with an LLM judge, so these numbers are not leaderboard-comparable."""

import argparse
import asyncio
import json
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from redis.asyncio import Redis

from app.agent.budget import Budget, DailyCap, estimated_cost_usd
from app.agent.filters import filter_findings
from app.agent.llm import GeminiLLM, LlmError
from app.agent.loop import run_agent, with_second_look
from app.agent.prompts import LOOK_AGAIN, build_context
from app.agent.tools import Tools
from app.checks.linters import run_linters
from app.core.config import get_settings
from app.github.diff import MAX_FILES, REVIEWED_SUFFIXES, PrFile, parse_patch

HERE = Path(__file__).parent
SEED = 2026  # fixed, so the slice can be reproduced
LANGUAGES = {"Python", "TypeScript"}  # what DiffMate reviews
TOLERANCE = 3
STOPPED = ("daily_cap", "rate_limited")


def pick(manifest: list[dict], count: int) -> list[dict]:
    """A seeded random slice of the Python and TypeScript PRs: no hand-picking."""
    pool = sorted((m for m in manifest if m["language"] in LANGUAGES), key=lambda m: m["pr_url"])
    return random.Random(SEED).sample(pool, min(count, len(pool)))  # noqa: S311 - sampling, not crypto


def key(m: dict) -> str:
    return f"{m['nwo'].replace('/', '_')}_{m['pr_number']}"


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-c", "core.hooksPath=/dev/null", *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    ).stdout


def checkout(m: dict, dest: Path) -> list[PrFile]:
    """Clone the PR's mirror at its head commit; return the reviewed files' diffs."""
    url = f"https://github.com/review-bench/{m['nwo'].replace('/', '_')}.git"
    _git("clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(dest), cwd=dest.parent)
    _git("checkout", "--quiet", m["head"], cwd=dest)
    files = []
    for line in _git(
        "diff", "--name-status", "--no-renames", m["base"], m["head"], cwd=dest
    ).splitlines():
        status, path = line.split("\t", 1)
        if status == "D" or not path.endswith(REVIEWED_SUFFIXES):
            continue
        patch = _git("diff", "-U3", m["base"], m["head"], "--", path, cwd=dest)
        hunks = patch[patch.find("@@") :] if "@@" in patch else ""
        files.append(
            PrFile(path, "added" if status == "A" else "modified", hunks, parse_patch(hunks))
        )
    return files[:MAX_FILES]


async def review(m: dict, llm, cap: DailyCap) -> dict:
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="diffmate-rb-") as tmp:
        root = Path(tmp) / "repo"
        files = checkout(m, root)
        if not files:
            return {
                "name": key(m),
                "files": 0,
                "posted": [],
                "stop_reason": "no_reviewable_files",
                "llm_requests": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "seconds": 0,
            }
        start = time.monotonic()
        hints = await run_linters(root, [f.path for f in files])
        context = build_context(m["title"], m["body"] or "", files, [str(h) for h in hints])
        budget = lambda: Budget(settings.agent_max_steps, settings.agent_max_tokens)  # noqa: E731
        result = await run_agent(llm, Tools(root, files), context, budget(), cap)
        commentable = {f.path: f.lines for f in files}
        statuses = filter_findings(result.findings, commentable, settings.confidence_threshold)
        if result.stop_reason == "submitted" and not any(s == "posted" for _, s in statuses):
            second = await run_agent(
                llm, Tools(root, files), f"{context}\n\n{LOOK_AGAIN}", budget(), cap
            )
            result = with_second_look(result, second)
            statuses = filter_findings(result.findings, commentable, settings.confidence_threshold)
        b = result.budget
        return {
            "name": key(m),
            "files": len(files),
            "posted": [f.model_dump() for f, s in statuses if s == "posted"],
            "stop_reason": result.stop_reason,
            "llm_requests": result.llm_requests,
            "tokens_in": b.tokens_in,
            "tokens_out": b.tokens_out,
            "cost_usd": estimated_cost_usd(settings.llm_model, b.tokens_in, b.tokens_out),
            "seconds": round(time.monotonic() - start, 1),
        }


def matches(note: dict, golden: dict) -> bool:
    return (
        note["file"] == golden["file"]
        and golden["start_line"] - TOLERANCE <= note["line"] <= golden["end_line"] + TOLERANCE
    )


def score_pr(posted: list[dict], golden: list[dict]) -> dict:
    """ReviewBench-style grounded counts with line-overlap matching. Candidates claim at most
    one golden finding each, in order; golden findings count once for recall."""
    tps = [i for i, g in enumerate(golden) if g["tp_fp"] == "tp"]
    covered = {i for i in tps if any(matches(n, golden[i]) for n in posted)}
    claimed, matched_tp, matched = set(), 0, 0
    for n in posted:
        hit = next((i for i, g in enumerate(golden) if i not in claimed and matches(n, g)), None)
        if hit is None:
            continue
        claimed.add(hit)
        matched += 1
        matched_tp += golden[hit]["tp_fp"] == "tp"
    reviewable = [i for i in tps if golden[i]["file"].endswith(REVIEWED_SUFFIXES)]
    return {
        "golden_tp": len(tps),
        "golden_tp_reviewable": len(reviewable),
        "covered": len(covered),
        "covered_reviewable": len(covered & set(reviewable)),
        "matched": matched,
        "matched_tp": matched_tp,
        "unmatched": len(posted) - matched,
        "notes": len(posted),
    }


def summarize(rows: list[dict], data: Path) -> dict:
    t = dict.fromkeys(
        [
            "golden_tp",
            "golden_tp_reviewable",
            "covered",
            "covered_reviewable",
            "matched",
            "matched_tp",
            "unmatched",
            "notes",
        ],
        0,
    )
    for r in rows:
        golden = json.loads((data / "golden" / r["golden_file"]).read_text())["findings"]
        for k, v in score_pr(r["posted"], golden).items():
            t[k] += v
    pct = lambda a, b: round(a / b, 3) if b else None  # noqa: E731
    return t | {
        "prs": len(rows),
        "grounded_recall": pct(t["covered"], t["golden_tp"]),
        "grounded_recall_reviewable_files": pct(t["covered_reviewable"], t["golden_tp_reviewable"]),
        "grounded_precision": pct(t["matched_tp"], t["matched"]),
        "requests": sum(r["llm_requests"] for r in rows),
    }


async def run(data: Path, count: int, model: str) -> int:
    settings = get_settings()
    key_ = settings.gemini_api_key.get_secret_value()
    if not key_:
        print("GEMINI_API_KEY is not set in .env", file=sys.stderr)
        return 2
    manifest = json.loads((data / "corpus" / "manifest.json").read_text())
    golden_files = {p.name.rsplit("-", 1)[0]: p.name for p in (data / "golden").glob("*.json")}
    llm = GeminiLLM(key_, model, settings.llm_thinking_level, settings.llm_timeout_seconds)
    redis = Redis.from_url(settings.redis_url)
    cap = DailyCap(
        redis,
        settings.llm_daily_request_cap or 400,
        settings.llm_requests_per_minute or 12,
        model=model,
    )
    out = HERE / "results" / f"reviewbench-{model}.jsonl"
    done = (
        {json.loads(line)["name"] for line in out.read_text().splitlines()}
        if out.exists()
        else set()
    )
    for m in pick(manifest, count):
        if key(m) in done:
            continue
        try:
            r = await review(m, llm, cap)
        except LlmError as e:
            print(f"stopped at {key(m)}: provider error ({e}). Re-run later.", flush=True)
            await redis.aclose()
            return 3
        except (subprocess.SubprocessError, OSError) as e:
            print(f"{key(m)}: checkout failed ({type(e).__name__}), skipped", flush=True)
            continue
        if r["stop_reason"] in STOPPED:
            print(f"stopped at {key(m)}: {r['stop_reason']}. Re-run later.", flush=True)
            await redis.aclose()
            return 3
        r["golden_file"] = golden_files[key(m)]
        with out.open("a") as f:
            f.write(json.dumps(r) + "\n")
        golden = json.loads((data / "golden" / r["golden_file"]).read_text())["findings"]
        s = score_pr(r["posted"], golden)
        print(
            f"{key(m):<60} notes={s['notes']} covered {s['covered']}/{s['golden_tp']} "
            f"requests={r['llm_requests']} {r['seconds']:.0f}s",
            flush=True,
        )
    await redis.aclose()
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    print(json.dumps(summarize(rows, data), indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["run", "score"])
    p.add_argument(
        "--data", type=Path, required=True, help="local clone of review-bench/ReviewBench"
    )
    p.add_argument("--count", type=int, default=30)
    p.add_argument("--model", default="gemini-3.5-flash-lite")
    a = p.parse_args()
    if a.command == "score":
        out = HERE / "results" / f"reviewbench-{a.model}.jsonl"
        rows = [json.loads(line) for line in out.read_text().splitlines()]
        print(json.dumps(summarize(rows, a.data), indent=2))
        return 0
    return asyncio.run(run(a.data, a.count, a.model))


if __name__ == "__main__":
    raise SystemExit(main())
