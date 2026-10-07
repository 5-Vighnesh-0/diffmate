import httpx
import pytest
from arq import Retry

from app.queue.jobs import enqueue_review, review_job_id
from app.queue.worker import review_pr

SHA = "a" * 40


def test_review_job_id_is_unique_per_repo_pr_and_commit():
    assert review_job_id("o/r", 7, SHA) == f"review:o/r:7:{SHA}"


async def test_enqueue_review_reports_duplicate_when_arq_refuses_the_job():
    class Pool:
        async def enqueue_job(self, *args, _job_id=None):
            return None  # what arq returns when a job with this ID already exists

    assert await enqueue_review(Pool(), repo="o/r", pr=7, sha=SHA, installation_id=1) is False


def github(comment_status=200, comment_error=None):
    """Fake GitHub: the token exchange works; every later call (starting with the PR
    details request) fails with the given status or error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/access_tokens"):
            return httpx.Response(201, json={"token": "inst-token"})
        if comment_error:
            raise comment_error
        return httpx.Response(comment_status, json={})

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.github.com"
    )
    return http, []


def ctx(http, job_try=1):
    return {"http": http, "app_jwt": lambda: "app-jwt", "job_try": job_try}


@pytest.mark.parametrize("status", [429, 500, 502])
async def test_github_server_errors_and_rate_limits_retry_with_backoff(status):
    http, _ = github(comment_status=status)

    with pytest.raises(Retry) as exc:
        await review_pr(ctx(http, job_try=2), "o/r", 7, SHA, 42)

    assert exc.value.defer_score == 20_000  # 5 s * 2**job_try, in ms


async def test_network_errors_retry():
    http, _ = github(comment_error=httpx.ConnectError("down"))

    with pytest.raises(Retry):
        await review_pr(ctx(http), "o/r", 7, SHA, 42)


async def test_client_errors_fail_without_retry():
    http, _ = github(comment_status=404)

    with pytest.raises(httpx.HTTPStatusError):
        await review_pr(ctx(http), "o/r", 7, SHA, 42)


async def test_last_try_raises_the_real_error_instead_of_a_wasted_retry():
    http, _ = github(comment_status=502)

    with pytest.raises(httpx.HTTPStatusError):
        await review_pr(ctx(http, job_try=3), "o/r", 7, SHA, 42)


@pytest.mark.parametrize("headers", [{"x-ratelimit-remaining": "0"}, {"retry-after": "60"}])
async def test_github_403_rate_limit_retries(headers):
    def handler(request):
        if request.url.path.endswith("/access_tokens"):
            return httpx.Response(201, json={"token": "t"})
        return httpx.Response(403, headers=headers, json={})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://x")

    with pytest.raises(Retry):
        await review_pr(ctx(http), "o/r", 7, SHA, 42)


async def test_plain_403_fails_without_retry():
    http, _ = github(comment_status=403)

    with pytest.raises(httpx.HTTPStatusError):
        await review_pr(ctx(http), "o/r", 7, SHA, 42)


async def test_startup_error_is_not_masked_by_shutdown():
    from app.queue.worker import shutdown

    await shutdown({})  # startup failed before creating the http client: must not raise
