import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import Finding, Installation, PullRequest, Repo, Run

SHA = "a" * 40


async def add_pr(s) -> PullRequest:
    inst = Installation(github_installation_id=1, account_login="o")
    repo = Repo(installation=inst, github_repo_id=2, full_name="o/r")
    pr = PullRequest(repo=repo, number=7, title="Fix it")
    s.add(pr)
    await s.commit()
    return pr


async def test_a_commit_can_have_only_one_run(session):
    pr = await add_pr(session)
    session.add(Run(pull_request_id=pr.id, commit_sha=SHA))
    await session.commit()

    session.add(Run(pull_request_id=pr.id, commit_sha=SHA))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_constraints_reject_out_of_range_findings(session):
    pr = await add_pr(session)
    run = Run(pull_request_id=pr.id, commit_sha=SHA)
    session.add(run)
    await session.commit()

    session.add(
        Finding(
            run_id=run.id,
            source="agent",
            file="a.py",
            line=1,
            category="bug",
            severity="high",
            confidence=1.5,
            explanation="x",
            status="posted",
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_upgrade_creates_the_nine_approved_tables(session):
    rows = await session.execute(
        text("select table_name from information_schema.tables where table_schema='public'")
    )
    tables = {r[0] for r in rows} - {"alembic_version"}

    assert tables == {
        "installations",
        "repos",
        "pull_requests",
        "runs",
        "findings",
        "trace_steps",
        "feedback",
        "benchmark_cases",
        "benchmark_runs",
    }


async def test_findings_can_be_stored_as_dropped_not_in_diff(session):
    pr = await add_pr(session)
    run = Run(pull_request_id=pr.id, commit_sha=SHA)
    session.add(run)
    await session.commit()

    session.add(
        Finding(
            run_id=run.id,
            source="agent",
            file="a.py",
            line=500,
            category="bug",
            severity="high",
            confidence=0.9,
            explanation="x",
            status="dropped_not_in_diff",
        )
    )
    await session.commit()
