import io
import json
import tarfile
from dataclasses import dataclass, field
from types import SimpleNamespace

import httpx
from sqlalchemy import select, text

from app.agent.llm import LlmStep, ToolCall
from app.db.models import Feedback, Finding, Installation, PullRequest, Repo, Run, TraceStep
from app.queue.worker import answer_reply, review_pr

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
        if nx and key in self.counts:
            return None
        self.counts[key] = int(value)
        return True


def tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("o-r-sha/calc.py")
        info.size = len(SOURCE)
        tar.addfile(info, io.BytesIO(SOURCE))
    return buf.getvalue()


def fake_github(reviews: list, private=False, replies=None, edits=None):
    replies = [] if replies is None else replies
    edits = [] if edits is None else edits

    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path.endswith("/access_tokens"):
            return httpx.Response(201, json={"token": "t"})
        if path == "/repos/o/r/pulls/7" and method == "GET":
            body = {
                "title": "Fix div",
                "body": "please",
                "base": {"repo": {"id": 555, "private": private}},
            }
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
        if path == "/repos/o/r/pulls/7/reviews/1/comments":
            comments = reviews[-1]["comments"] if reviews else []
            listed = [
                {
                    "id": 100 + i,
                    "path": c["path"],
                    "line": c["line"],
                    "start_line": c.get("start_line"),
                    "body": c["body"],
                }
                for i, c in enumerate(comments)
            ]
            return httpx.Response(200, json=listed)
        if path.startswith("/repos/o/r/pulls/7/comments/") and path.endswith("/replies"):
            replies.append(json.loads(request.content)["body"])
            return httpx.Response(201, json={})
        if path.startswith("/repos/o/r/pulls/comments/") and method == "PATCH":
            edits.append((int(path.rsplit("/", 1)[1]), json.loads(request.content)["body"]))
            return httpx.Response(200, json={})
        return httpx.Response(404, json={})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://x")


def ctx(sessionmaker, llm, reviews, cap=100, private=False, replies=None, edits=None):
    settings = SimpleNamespace(
        llm_model="gemini-3.8-flash",
        llm_daily_request_cap=cap,
        llm_requests_per_minute=0,
        agent_max_steps=8,
        agent_max_tokens=60_000,
        confidence_threshold=0.7,
        strict_confidence_threshold=0.9,
        comment_cap=5,
    )
    return {
        "http": fake_github(reviews, private, replies, edits),
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
    run = (await session.execute(select(Run))).scalar_one()
    await session.refresh(run)
    assert run.status == "done"
    steps = (await session.execute(select(TraceStep.step_no))).scalars().all()
    assert sorted(steps) == [1, 2]  # the old attempt's trace was replaced, not duplicated
    assert len((await session.execute(select(Finding))).scalars().all()) == 3


async def test_a_paused_run_resumes_with_a_fresh_trace_and_findings(sessionmaker, session):
    reviews = []
    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)
    await session.execute(text("update runs set status='paused_daily_cap'"))
    await session.commit()

    await review_pr(ctx(sessionmaker, reviewing_llm(), reviews), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    await session.refresh(run)
    assert run.status == "done"
    assert len((await session.execute(select(TraceStep))).scalars().all()) == 2
    assert len((await session.execute(select(Finding))).scalars().all()) == 3


async def test_a_private_repository_is_never_sent_to_the_ai(sessionmaker, session):
    reviews, llm = [], reviewing_llm()

    await review_pr(ctx(sessionmaker, llm, reviews, private=True), "o/r", 7, SHA, 42)

    assert (llm.calls, reviews) == (0, [])
    assert (await session.execute(select(Run))).scalars().all() == []


async def test_provider_rate_limit_pauses_the_run_and_posts_nothing(sessionmaker, session):
    from app.agent.llm import LlmRateLimited

    reviews = []
    limited = FakeLLM([], error=LlmRateLimited("429"))

    await review_pr(ctx(sessionmaker, limited, reviews), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, reviews) == ("paused_daily_cap", [])


async def test_a_category_this_repo_voted_not_useful_needs_more_confidence(sessionmaker, session):
    # Earlier, people on o/r marked 2 of 3 bug notes Not useful.
    repo = Repo(
        installation=Installation(github_installation_id=42, account_login="o"),
        github_repo_id=555,
        full_name="o/r",
    )
    old = PullRequest(repo=repo, number=1, title="old")
    session.add(old)
    await session.flush()
    old_run = Run(pull_request_id=old.id, commit_sha="b" * 40, status="done")
    session.add(old_run)
    await session.flush()
    for user, verdict in [(1, "reject"), (2, "reject"), (3, "accept")]:
        note = Finding(
            run_id=old_run.id,
            source="agent",
            file="calc.py",
            line=user,
            category="bug",
            severity="low",
            confidence=0.8,
            explanation="x",
            status="posted",
        )
        session.add(note)
        await session.flush()
        session.add(Feedback(finding_id=note.id, github_user_id=user, verdict=verdict))
    await session.commit()
    security = {**finding(3, 0.8), "category": "security"}
    llm = FakeLLM([("submit_findings", {"findings": [finding(2, 0.8), security]})])
    reviews = []

    await review_pr(ctx(sessionmaker, llm, reviews), "o/r", 7, SHA, 42)

    assert [(c["line"]) for c in reviews[0]["comments"]] == [3]
    new = (await session.execute(select(Finding).where(Finding.run_id != old_run.id))).scalars()
    assert sorted((f.line, f.status) for f in new) == [(2, "dropped_stricter"), (3, "posted")]


async def test_a_sure_note_with_a_fix_is_posted_as_a_one_click_suggestion(sessionmaker, session):
    sure = {**finding(2, 0.97), "fix": "    return a / b"}
    llm = FakeLLM([("submit_findings", {"findings": [sure]})])
    reviews = []

    await review_pr(ctx(sessionmaker, llm, reviews), "o/r", 7, SHA, 42)

    assert "```suggestion\n    return a / b\n```" in reviews[0]["comments"][0]["body"]
    stored = (await session.execute(select(Finding))).scalar_one()
    assert (stored.line, stored.status) == (2, "posted")


async def reviewed(sessionmaker, replies, edits):
    """Run one review that posts a note on calc.py line 2; return the context to reuse."""
    reviews = []
    c = ctx(sessionmaker, reviewing_llm(), reviews, replies=replies, edits=edits)
    await review_pr(c, "o/r", 7, SHA, 42)
    return c


def answering(*answers):
    return FakeLLM([("answer", {"verdict": v, "reply": r}) for v, r in answers])


async def test_posted_notes_remember_their_github_comment(sessionmaker, session):
    await reviewed(sessionmaker, [], [])

    posted = (await session.execute(select(Finding).where(Finding.status == "posted"))).scalar_one()
    assert posted.github_comment_id == 100


async def test_diffmate_stands_by_a_note_with_a_reason(sessionmaker, session):
    replies, edits = [], []
    c = await reviewed(sessionmaker, replies, edits)
    c["llm"] = answering(("stand", "b can be 0 when the list is empty, so this still fails."))

    await answer_reply(c, "o/r", 7, 42, 100, "b is never 0 here", "@@ hunk", 9)

    assert replies == ["b can be 0 when the list is empty, so this still fails."]
    assert edits == []
    assert (await session.execute(select(Feedback))).scalars().all() == []


async def test_diffmate_withdraws_a_wrong_note_and_counts_it_as_not_useful(sessionmaker, session):
    replies, edits = [], []
    c = await reviewed(sessionmaker, replies, edits)
    c["llm"] = answering(("withdraw", "You are right, the caller checks b first."))

    await answer_reply(c, "o/r", 7, 42, 100, "the caller checks b", "@@ hunk", 9)

    assert replies == ["You are right, the caller checks b first."]
    assert edits[0][0] == 100 and edits[0][1].startswith("**Withdrawn:**")
    vote = (await session.execute(select(Feedback))).scalar_one()
    assert (vote.github_user_id, vote.verdict) == (9, "reject")


async def test_a_reply_to_someone_elses_comment_is_ignored(sessionmaker):
    replies = []
    c = await reviewed(sessionmaker, replies, [])
    c["llm"] = llm = answering(("stand", "x"))

    await answer_reply(c, "o/r", 7, 42, 555, "hello", "@@", 9)

    assert (llm.calls, replies) == (0, [])


async def test_one_note_gets_at_most_three_answers(sessionmaker):
    replies = []
    c = await reviewed(sessionmaker, replies, [])
    c["llm"] = llm = answering(*[("stand", f"answer {i}") for i in range(4)])

    for _ in range(4):
        await answer_reply(c, "o/r", 7, 42, 100, "really?", "@@", 9)

    assert llm.calls == 3 and len(replies) == 3


async def test_a_review_that_stops_early_is_not_shown_as_clean(sessionmaker, session):
    # The AI keeps reading and never submits: the run hits its step cap with no findings.
    llm = FakeLLM([("read_file", {"path": "calc.py"})] * 8)
    reviews = []

    await review_pr(ctx(sessionmaker, llm, reviews), "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert run.status == "done" and reviews == []
    assert run.error.startswith("Stopped early")


async def test_two_notes_on_one_line_keep_their_own_github_comment(sessionmaker, session):
    security = {**finding(2, 0.9), "category": "security", "explanation": "unsafe"}
    llm = FakeLLM([("submit_findings", {"findings": [finding(2, 0.9), security]})])

    await review_pr(ctx(sessionmaker, llm, []), "o/r", 7, SHA, 42)

    stored = (await session.execute(select(Finding).order_by(Finding.category))).scalars().all()
    assert sorted(f.github_comment_id for f in stored) == [100, 101]


async def test_a_github_hiccup_after_posting_does_not_fail_the_review(sessionmaker, session):
    c = ctx(sessionmaker, reviewing_llm(), [])
    inner = c["http"]._transport.handler

    def flaky(request):
        if request.url.path.endswith("/reviews/1/comments"):
            return httpx.Response(502, json={})
        return inner(request)

    c["http"] = httpx.AsyncClient(transport=httpx.MockTransport(flaky), base_url="https://x")
    await review_pr(c, "o/r", 7, SHA, 42)

    run = (await session.execute(select(Run))).scalar_one()
    assert run.status == "done"


async def test_a_withdrawn_note_is_not_argued_about_again(sessionmaker):
    replies = []
    c = await reviewed(sessionmaker, replies, [])
    c["llm"] = llm = answering(("withdraw", "You are right."), ("stand", "Actually no."))

    await answer_reply(c, "o/r", 7, 42, 100, "wrong", "@@", 9)
    await answer_reply(c, "o/r", 7, 42, 100, "still wrong?", "@@", 9)

    assert llm.calls == 1 and replies == ["You are right."]


async def test_a_review_that_finds_nothing_takes_one_focused_second_look(sessionmaker, session):
    llm = FakeLLM(
        [
            ("submit_findings", {"findings": []}),  # first pass: nothing
            ("submit_findings", {"findings": [finding(2, 0.9)]}),  # second look finds the bug
        ]
    )
    reviews = []

    await review_pr(ctx(sessionmaker, llm, reviews), "o/r", 7, SHA, 42)

    assert llm.calls == 2
    assert [c["line"] for c in reviews[0]["comments"]] == [2]
    run = (await session.execute(select(Run))).scalar_one()
    assert (run.status, run.llm_requests) == ("done", 2)
    steps = (await session.execute(select(TraceStep).order_by(TraceStep.step_no))).scalars().all()
    assert [s.step_no for s in steps] == [1, 2]


async def test_no_second_look_when_the_first_pass_already_posted(sessionmaker):
    llm = reviewing_llm()

    await review_pr(ctx(sessionmaker, llm, []), "o/r", 7, SHA, 42)

    assert llm.calls == 2  # read_file + submit, nothing more


async def test_a_two_line_fix_keeps_its_note_linked_to_the_github_comment(sessionmaker, session):
    sure = {**finding(2, 0.97), "fix": "    return a / b\nx = 1", "fix_end_line": 3}
    reviews = []

    await review_pr(
        ctx(sessionmaker, FakeLLM([("submit_findings", {"findings": [sure]})]), reviews),
        "o/r",
        7,
        SHA,
        42,
    )

    (c,) = reviews[0]["comments"]
    assert (c["start_line"], c["line"]) == (2, 3)
    stored = (await session.execute(select(Finding))).scalar_one()
    assert (stored.line, stored.github_comment_id) == (2, 100)
