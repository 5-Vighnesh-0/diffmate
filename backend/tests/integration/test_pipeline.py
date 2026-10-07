import io
import json
import tarfile
from dataclasses import dataclass, field
from types import SimpleNamespace

import httpx
from sqlalchemy import select

from app.agent.llm import LlmStep, ToolCall
from app.db.models import Finding, Run, TraceStep
from app.queue.worker import review_pr

SHA = "a" * 40
PATCH = "@@ -1,2 +1,3 @@\n def div(a, b):\n-    return a / b\n+    return a // b\n+x = 1"
SOURCE = b"def div(a, b):\n    return a // b\nx = 1\n"


def finding(line, confidence):
    return {
        "file": "calc.py",
        "line": line,
        "category": "bug",
        "severity": "high",
        "confidence": confidence,
        "explanation": f"problem at {line}",
    }


@dataclass
class FakeLLM:
    script: list
    calls: int = 0
    error: Exception | None = None

    async def step(self, system, history, tools, max_output_tokens):
        if self.error:
            raise self.error
        name, args = self.script[self.calls]
        self.calls += 1
        call = ToolCall(id=f"c{self.calls}", name=name, arguments=args)
        return LlmStep([call], "", 2_000, 300, [{"type": "function_call", "id": call.id}])


@dataclass
class FakeRedis:
    counts: dict = field(default_factory=dict)

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        pass

    async def set(self, key, value, nx=False, ex=None):
        pass


def tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("o-r-sha/calc.py")
        info.size = len(SOURCE)
        tar.addfile(info, io.BytesIO(SOURCE))
    return buf.getvalue()


def fake_github(reviews: list):
    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path.endswith("/access_tokens"):
            return httpx.Response(201, json={"token": "t"})
        if path == "/repos/o/r/pulls/7" and method == "GET":
            body = {"title": "Fix div", "body": "please", "base": {"repo": {"id": 555}}}
            return httpx.Response(200, json=body)
        if path == "/repos/o/r/pulls/7/files":
            return httpx.Response(
                200, json=[{"filename": "calc.py", "status": "modified", "patch": PATCH}]
            )
        if path == f"/repos/o/r/tarball/{SHA}":
            return httpx.Response(200, content=tarball())
        if path == "/repos/o/r/pulls/7/reviews" and method == "GET":
            return httpx.Response(200, json=reviews)
        if path == "/repos/o/r/pulls/7/reviews" and method == "POST":
            reviews.append(json.loads(request.content))
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(404, json={})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://x")


def ctx(sessionmaker, llm, reviews, cap=100):
    settings = SimpleNamespace(
        llm_model="gemini-3.8-flash",
        llm_daily_request_cap=cap,
        llm_requests_per_minute=0,
        agent_max_steps=8,
        agent_max_tokens=60_000,
        confidence_threshold=0.7,
        comment_cap=5,
    )
    return {
        "http": fake_github(reviews),
        "app_jwt": lambda: "jwt",
        "job_try": 1,
        "settings": settings,
        "db": sessionmaker,
        "llm": llm,
        "redis": FakeRedis(),
    }


def reviewing_llm():
    return FakeLLM(
        [
            ("read_file", {"path": "calc.py"}),
            ("submit_findings", {"findings": [finding(2, 0.9), finding(3, 0.5), finding(50, 0.9)]}),
        ]
    )


async def test_review_posts_filtered_findings_and_records_the_run(sessionmaker, session):
    reviews = []

    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)

    assert len(reviews) == 1
    assert [(c["path"], c["line"]) for c in reviews[0]["comments"]] == [("calc.py", 2)]
    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, run.llm_requests, run.tokens_in, run.tokens_out) == ("done", 2, 4000, 600)
    assert run.est_cost_usd > 0
    stored = (await session.execute(select(Finding).order_by(Finding.line))).scalars().all()
    assert [(f.line, f.status) for f in stored] == [
        (2, "posted"),
        (3, "dropped_low_confidence"),
        (50, "dropped_not_in_diff"),
    ]
    trace = (await session.execute(select(TraceStep).order_by(TraceStep.step_no))).scalars().all()
    assert [t.tool for t in trace] == ["read_file", "submit_findings"]


async def test_the_same_commit_is_reviewed_only_once(sessionmaker):
    reviews = []
    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)
    again = reviewing_llm()

    await review_pr(ctx(sessionmaker, again, reviews), "o/r", 7, SHA, 42)

    assert again.calls == 0
    assert len(reviews) == 1


async def test_daily_cap_pauses_the_run_and_posts_nothing(sessionmaker, session):
    reviews, llm = [], reviewing_llm()

    await review_pr(ctx(sessionmaker, llm, reviews, cap=0), "o/r", 7, SHA, 42)

    assert (llm.calls, reviews) == (0, [])
    run = (await session.execute(select(Run))).scalar_one()
    assert run.status == "paused_daily_cap"


async def test_llm_failure_marks_the_run_failed_posts_nothing_and_can_be_retried(
    sessionmaker, session
):
    reviews = []
    broken = FakeLLM([], error=RuntimeError("model unavailable"))

    await review_pr(ctx(sessionmaker, broken, reviews), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, run.error, reviews) == ("failed", "RuntimeError", [])

    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)

    await session.refresh(run)
    assert run.status == "done"
    assert len(reviews) == 1


async def test_a_cancelled_job_is_recorded_as_failed_so_it_can_be_retried(sessionmaker, session):
    import asyncio

    import pytest

    cancelled = FakeLLM([], error=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await review_pr(ctx(sessionmaker, cancelled, []), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, run.error) == ("failed", "Cancelled")


async def test_a_run_left_running_by_a_crash_is_reclaimed_after_the_job_timeout(
    sessionmaker, session
):
    from sqlalchemy import text

    reviews = []
    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)
    await session.execute(
        text("update runs set status='running', started_at=now() - interval '20 minutes'")
    )
    await session.commit()
    reviews.clear()

    llm = reviewing_llm()
    await review_pr(ctx(sessionmaker, llm, reviews), "o/r", 7, SHA, 42)

    assert llm.calls == 2


async def test_provider_rate_limit_pauses_the_run_and_posts_nothing(sessionmaker, session):
    from app.agent.llm import LlmRateLimited

    reviews = []
    limited = FakeLLM([], error=LlmRateLimited("429"))

    await review_pr(ctx(sessionmaker, limited, reviews), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, reviews) == ("paused_daily_cap", [])
