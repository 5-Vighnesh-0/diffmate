import logging
import time
from pathlib import Path

import httpx
from arq import Retry, func
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.github.app_auth import get_installation_token, make_app_jwt
from app.github.client import github_http
from app.github.comments import post_issue_comment

log = logging.getLogger(__name__)


MAX_TRIES = 3


def _retryable(error: Exception) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        r = error.response
        # GitHub signals rate limits with 429, or with 403 plus rate-limit headers.
        rate_limited = r.status_code == 403 and (
            r.headers.get("x-ratelimit-remaining") == "0" or "retry-after" in r.headers
        )
        return rate_limited or r.status_code == 429 or r.status_code >= 500
    return isinstance(error, httpx.TransportError)


async def review_pr(ctx, repo: str, pr: int, sha: str, installation_id: int) -> None:
    # Phase 1: prove the pipeline with one comment. Phase 2 replaces this with the review.
    http = ctx["http"]
    try:
        token = await get_installation_token(
            http, ctx["app_jwt"](), installation_id, repo.split("/")[1]
        )
        await post_issue_comment(
            http,
            token,
            repo,
            pr,
            f"DiffMate received commit `{sha[:7]}`. Automated review is not enabled yet.",
        )
    except (httpx.TransportError, httpx.HTTPStatusError) as e:
        # On the last try, raise the real error: a Retry there would only be refused by arq.
        if _retryable(e) and ctx["job_try"] < MAX_TRIES:
            log.warning("review %s#%s try %s failed, retrying", repo, pr, ctx["job_try"])
            raise Retry(defer=5 * 2 ** ctx["job_try"]) from e
        raise


async def startup(ctx) -> None:
    setup_logging()
    settings = get_settings()
    if settings.github_app_id is None or not settings.github_app_private_key_path:
        raise RuntimeError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH must be set")
    key = Path(settings.github_app_private_key_path).read_text()
    app_id = settings.github_app_id
    ctx["http"] = github_http()
    ctx["app_jwt"] = lambda: make_app_jwt(app_id, key, int(time.time()))


async def shutdown(ctx) -> None:
    # startup may have failed before creating the client; don't hide its error.
    if http := ctx.get("http"):
        await http.aclose()


class WorkerSettings:
    functions = [func(review_pr, max_tries=MAX_TRIES)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    keep_result = 7 * 24 * 3600  # job ID stays taken for 7 days -> one run per commit
