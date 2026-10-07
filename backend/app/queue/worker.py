import asyncio
import logging
import tempfile
import time
from datetime import timedelta
from pathlib import Path

import httpx
from arq import Retry, func
from arq.connections import RedisSettings
from sqlalchemy import func as sql
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from app.agent.budget import Budget, DailyCap, estimated_cost_usd
from app.agent.filters import filter_findings
from app.agent.llm import GeminiLLM
from app.agent.loop import AgentResult, run_agent
from app.agent.prompts import build_context
from app.agent.tools import Tools
from app.checks.linters import run_linters
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.models import Finding, Installation, PullRequest, Repo, Run, TraceStep
from app.db.session import make_engine, make_sessionmaker
from app.github.app_auth import get_installation_token, make_app_jwt
from app.github.client import github_http
from app.github.comments import post_review
from app.github.diff import PullInfo, checkout, get_pr_files, get_pull_request

log = logging.getLogger(__name__)

MAX_TRIES = 3
RETRYABLE_RUN_STATUSES = ("failed", "paused_daily_cap")
JOB_TIMEOUT_SECONDS = 900  # worst case 8 steps x 90 s LLM timeout = 720 s


def _retryable(error: Exception) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        r = error.response
        # GitHub signals rate limits with 429, or with 403 plus rate-limit headers.
        rate_limited = r.status_code == 403 and (
            r.headers.get("x-ratelimit-remaining") == "0" or "retry-after" in r.headers
        )
        return rate_limited or r.status_code == 429 or r.status_code >= 500
    return isinstance(error, httpx.TransportError)


async def claim_run(db, installation_id: int, repo: str, pr: int, sha: str, info: PullInfo):
    """Create the run row for this commit, or re-open a failed, paused, or abandoned one.
    None means another run already did or is doing this commit."""
    owner = repo.split("/")[0]
    title = info.title[:300]
    async with db() as s, s.begin():
        inst_id = await s.scalar(
            insert(Installation)
            .values(github_installation_id=installation_id, account_login=owner)
            .on_conflict_do_update(
                index_elements=["github_installation_id"], set_={"account_login": owner}
            )
            .returning(Installation.id)
        )
        repo_id = await s.scalar(
            insert(Repo)
            .values(installation_id=inst_id, github_repo_id=info.github_repo_id, full_name=repo)
            .on_conflict_do_update(
                index_elements=["github_repo_id"],
                set_={"full_name": repo, "installation_id": inst_id},
            )
            .returning(Repo.id)
        )
        pr_id = await s.scalar(
            insert(PullRequest)
            .values(repo_id=repo_id, number=pr, title=title)
            .on_conflict_do_update(index_elements=["repo_id", "number"], set_={"title": title})
            .returning(PullRequest.id)
        )
        run_id = await s.scalar(
            insert(Run)
            .values(pull_request_id=pr_id, commit_sha=sha, status="running", started_at=sql.now())
            .on_conflict_do_nothing(index_elements=["pull_request_id", "commit_sha"])
            .returning(Run.id)
        )
        if run_id is None:
            run_id = await s.scalar(
                update(Run)
                .where(
                    Run.pull_request_id == pr_id,
                    Run.commit_sha == sha,
                    # failed/paused, or "running" past the job timeout (the worker crashed)
                    Run.status.in_(RETRYABLE_RUN_STATUSES)
                    | (
                        (Run.status == "running")
                        & (Run.started_at < sql.now() - timedelta(seconds=JOB_TIMEOUT_SECONDS))
                    ),
                )
                .values(status="running", error=None, started_at=sql.now(), finished_at=None)
                .returning(Run.id)
            )
        return run_id


async def save_result(
    db,
    run_id: int,
    status: str,
    model: str = "",
    result: AgentResult | None = None,
    statuses=(),
    error: str | None = None,
) -> None:
    async with db() as s, s.begin():
        values = {"status": status, "finished_at": sql.now(), "error": error}
        if result:
            b = result.budget
            values |= {
                "llm_requests": result.llm_requests,
                "tokens_in": b.tokens_in,
                "tokens_out": b.tokens_out,
                "est_cost_usd": estimated_cost_usd(model, b.tokens_in, b.tokens_out),
            }
            for f, finding_status in statuses:
                s.add(
                    Finding(run_id=run_id, source="agent", status=finding_status, **f.model_dump())
                )
            for n, t in enumerate(result.trace, 1):
                s.add(
                    TraceStep(
                        run_id=run_id,
                        step_no=n,
                        tool=t.tool[:100],
                        summary=t.summary,
                        tokens_in=t.tokens_in,
                        tokens_out=t.tokens_out,
                        duration_ms=t.duration_ms,
                    )
                )
        await s.execute(update(Run).where(Run.id == run_id).values(**values))


async def _review(ctx, token: str, run_id: int, repo: str, pr: int, sha: str, info: PullInfo):
    http, settings, llm = ctx["http"], ctx["settings"], ctx["llm"]
    if llm is None:
        raise RuntimeError("LLM is not configured")
    files = await get_pr_files(http, token, repo, pr)
    if not files:
        await save_result(ctx["db"], run_id, "done")
        return

    started = time.monotonic()
    # The checkout lives only for this run; the folder is deleted on exit (no code is stored).
    with tempfile.TemporaryDirectory(prefix="diffmate-") as tmp:
        root = await checkout(http, token, repo, sha, Path(tmp))
        hints = await run_linters(root, [f.path for f in files])
        context = build_context(info.title, info.body, files, [str(h) for h in hints])
        result = await run_agent(
            llm,
            Tools(root, files),
            context,
            Budget(settings.agent_max_steps, settings.agent_max_tokens),
            DailyCap(
                ctx["redis"], settings.llm_daily_request_cap, settings.llm_requests_per_minute
            ),
        )

    statuses = filter_findings(
        result.findings,
        {f.path: f.lines for f in files},
        settings.confidence_threshold,
        settings.comment_cap,
    )
    if result.stop_reason in ("daily_cap", "rate_limited"):
        status = "paused_daily_cap"  # nothing is posted; a later delivery can resume it
    else:
        status = "done"
        await post_review(http, token, repo, pr, sha, [f for f, s in statuses if s == "posted"])
    await save_result(ctx["db"], run_id, status, settings.llm_model, result, statuses)
    log.info(
        "review %s#%s@%s %s: %s posted, stop=%s, %d ms",
        repo,
        pr,
        sha[:7],
        status,
        sum(s == "posted" for _, s in statuses),
        result.stop_reason,
        int((time.monotonic() - started) * 1000),
    )


async def review_pr(ctx, repo: str, pr: int, sha: str, installation_id: int) -> None:
    http = ctx["http"]
    run_id = None
    try:
        token = await get_installation_token(
            http, ctx["app_jwt"](), installation_id, repo.split("/")[1]
        )
        info = await get_pull_request(http, token, repo, pr)
        run_id = await claim_run(ctx["db"], installation_id, repo, pr, sha, info)
        if run_id is None:
            log.info("review %s#%s@%s already done, skipping", repo, pr, sha[:7])
            return
        await _review(ctx, token, run_id, repo, pr, sha, info)
    except (httpx.TransportError, httpx.HTTPStatusError) as e:
        if run_id is not None:
            await save_result(ctx["db"], run_id, "failed", error=type(e).__name__)
        # On the last try, raise the real error: a Retry there would only be refused by arq.
        if _retryable(e) and ctx["job_try"] < MAX_TRIES:
            log.warning("review %s#%s try %s failed, retrying", repo, pr, ctx["job_try"])
            raise Retry(defer=5 * 2 ** ctx["job_try"]) from e
        raise
    except asyncio.CancelledError:
        # arq cancels a job at job_timeout; record it so the commit is not stuck in "running".
        if run_id is not None:
            await asyncio.shield(save_result(ctx["db"], run_id, "failed", error="Cancelled"))
        raise
    except Exception as e:
        if run_id is None:
            raise
        # LLM or checkout failure: nothing is posted, the run shows as failed (no retry: quota).
        log.exception("review %s#%s@%s failed", repo, pr, sha[:7])
        await save_result(ctx["db"], run_id, "failed", error=type(e).__name__)


async def startup(ctx) -> None:
    setup_logging()
    settings = get_settings()
    if settings.github_app_id is None or not settings.github_app_private_key_path:
        raise RuntimeError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH must be set")
    key = Path(settings.github_app_private_key_path).read_text()
    app_id = settings.github_app_id
    ctx["settings"] = settings
    ctx["http"] = github_http()
    ctx["app_jwt"] = lambda: make_app_jwt(app_id, key, int(time.time()))
    ctx["engine"] = make_engine(settings.database_url)
    ctx["db"] = make_sessionmaker(ctx["engine"])
    api_key = settings.gemini_api_key.get_secret_value()
    ctx["llm"] = (
        GeminiLLM(
            api_key, settings.llm_model, settings.llm_thinking_level, settings.llm_timeout_seconds
        )
        if api_key
        else None
    )


async def shutdown(ctx) -> None:
    # startup may have failed before creating these; don't hide its error.
    if http := ctx.get("http"):
        await http.aclose()
    if engine := ctx.get("engine"):
        await engine.dispose()


class WorkerSettings:
    functions = [func(review_pr, max_tries=MAX_TRIES)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = JOB_TIMEOUT_SECONDS
    # The runs table (unique PR + SHA) decides "one review per commit"; arq only needs to drop
    # duplicates while a job is queued or running, so failed commits stay retryable.
    keep_result = 60
