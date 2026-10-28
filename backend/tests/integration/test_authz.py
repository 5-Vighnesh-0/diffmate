"""A user sees and touches only runs from their own installations (other tenants -> 404)."""

import httpx
import pytest

from app.api.deps import get_db
from app.core.sessions import SESSION_COOKIE, create_session
from app.db.models import Finding, Installation, PullRequest, Repo, Run, TraceStep
from app.main import create_app

SHA = "a" * 40


async def seed(s, installation, repo_id, existing_installation=False):
    from sqlalchemy import select

    if existing_installation:
        inst = await s.scalar(
            select(Installation).where(Installation.github_installation_id == installation)
        )
    else:
        inst = Installation(github_installation_id=installation, account_login=f"o{installation}")
    repo = Repo(installation=inst, github_repo_id=repo_id, full_name=f"o{installation}/r{repo_id}")
    pr = PullRequest(repo=repo, number=1, title="t")
    s.add(pr)
    await s.flush()
    run = Run(pull_request_id=pr.id, commit_sha=SHA, status="done")
    s.add(run)
    await s.flush()
    finding = Finding(
        run_id=run.id,
        source="agent",
        file="a.py",
        line=1,
        category="bug",
        severity="high",
        confidence=0.9,
        explanation="<script>alert(1)</script>",
        status="posted",
    )
    s.add_all([finding, TraceStep(run_id=run.id, step_no=1, tool="read_file", summary="x")])
    await s.commit()
    return run.id, finding.id


@pytest.fixture
async def world(sessionmaker):
    from app.api.deps import get_redis
    from tests.conftest import FakeRedis

    async with sessionmaker() as s:
        mine = await seed(s, 42, 1)
        theirs = await seed(s, 99, 2)
        hidden = await seed(s, 42, 3, existing_installation=True)

    redis = FakeRedis()
    # Member of installation 42, but allowed to see only repo 1 (not repo 3 in the same org).
    sid, session = await create_session(redis, 7, "me", [42], [1])
    app = create_app()

    async def db():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE, sid)
        yield client, session.csrf, mine, theirs, hidden


async def test_run_list_shows_only_my_installations(world):
    client, _, (my_run, _), _, _ = world

    body = (await client.get("/api/runs")).json()

    assert [item["id"] for item in body["items"]] == [my_run]
    assert body["items"][0]["repo"] == "o42/r1"


async def test_other_tenants_runs_and_traces_are_404(world):
    client, _, _, (their_run, _), _ = world

    assert (await client.get(f"/api/runs/{their_run}")).status_code == 404
    assert (await client.get(f"/api/runs/{their_run}/trace")).status_code == 404


async def test_my_run_detail_returns_findings_as_plain_data(world):
    client, _, (my_run, _), _, _ = world

    run = (await client.get(f"/api/runs/{my_run}")).json()

    assert run["findings"][0]["explanation"] == "<script>alert(1)</script>"
    assert run["findings"][0]["my_verdict"] is None
    assert [t["tool"] for t in (await client.get(f"/api/runs/{my_run}/trace")).json()] == [
        "read_file"
    ]


async def test_feedback_requires_csrf_and_keeps_one_vote_per_user(world):
    client, csrf, (_, my_finding), _, _ = world
    url = f"/api/findings/{my_finding}/feedback"

    no_csrf = await client.post(url, json={"verdict": "accept"})
    first = await client.post(url, json={"verdict": "accept"}, headers={"X-CSRF-Token": csrf})
    changed = await client.post(url, json={"verdict": "reject"}, headers={"X-CSRF-Token": csrf})
    bad = await client.post(url, json={"verdict": "maybe"}, headers={"X-CSRF-Token": csrf})

    assert (no_csrf.status_code, first.status_code, changed.status_code) == (403, 204, 204)
    assert bad.status_code == 422


async def test_feedback_on_another_tenants_finding_is_404(world):
    client, csrf, _, (_, their_finding), _ = world

    r = await client.post(
        f"/api/findings/{their_finding}/feedback",
        json={"verdict": "reject"},
        headers={"X-CSRF-Token": csrf},
    )

    assert r.status_code == 404


async def test_no_session_is_401(world):
    client, *_ = world
    client.cookies.clear()

    assert (await client.get("/api/runs")).status_code == 401


async def test_a_repo_i_cannot_access_in_my_own_installation_is_hidden(world):
    client, csrf, _, _, (hidden_run, hidden_finding) = world

    assert (await client.get(f"/api/runs/{hidden_run}")).status_code == 404
    r = await client.post(
        f"/api/findings/{hidden_finding}/feedback",
        json={"verdict": "accept"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 404


async def test_feedback_summary_counts_only_my_votes_and_follows_changes(world):
    client, csrf, (_, my_finding), _, _ = world
    vote = f"/api/findings/{my_finding}/feedback"

    assert (await client.get("/api/feedback/summary")).json() == {
        "useful": 0,
        "not_useful": 0,
        "stricter": [],
    }

    await client.post(vote, json={"verdict": "accept"}, headers={"X-CSRF-Token": csrf})
    assert (await client.get("/api/feedback/summary")).json() == {
        "useful": 1,
        "not_useful": 0,
        "stricter": [],
    }

    await client.post(vote, json={"verdict": "reject"}, headers={"X-CSRF-Token": csrf})
    assert (await client.get("/api/feedback/summary")).json() == {
        "useful": 0,
        "not_useful": 1,
        "stricter": [],
    }

    client.cookies.clear()
    assert (await client.get("/api/feedback/summary")).status_code == 401


async def test_feedback_summary_lists_stricter_categories_only_for_my_repos(world, sessionmaker):
    from app.db.models import Feedback

    client, _, (_, my_finding), _, (_, hidden_finding) = world
    async with sessionmaker() as s:
        for finding_id in (my_finding, hidden_finding):
            for user, verdict in [(1, "reject"), (2, "reject"), (3, "accept")]:
                s.add(Feedback(finding_id=finding_id, github_user_id=user, verdict=verdict))
        await s.commit()

    body = (await client.get("/api/feedback/summary")).json()

    assert body["stricter"] == [{"repo": "o42/r1", "category": "bug", "not_useful": 2, "total": 3}]
