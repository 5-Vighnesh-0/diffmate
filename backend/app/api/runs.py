"""Dashboard reads. Every query is filtered by the session's installations AND the repos the
user can access in them (org membership alone is not enough); anything else
is reported as 404 so other tenants' IDs are not even confirmed to exist."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import get_db, get_session
from app.core.sessions import Session
from app.db.models import Feedback, Finding, Installation, PullRequest, Repo, Run, TraceStep

router = APIRouter()


def _my_runs(session: Session):
    return (
        select(Run, Repo.full_name, PullRequest.number, PullRequest.title)
        .join(PullRequest, PullRequest.id == Run.pull_request_id)
        .join(Repo, Repo.id == PullRequest.repo_id)
        .join(Installation, Installation.id == Repo.installation_id)
        .where(
            Installation.github_installation_id.in_(session.installation_ids),
            Repo.github_repo_id.in_(session.repo_ids),
        )
    )


def _run_json(run: Run, repo: str, pr: int, title: str) -> dict:
    return {
        "id": run.id,
        "repo": repo,
        "pr": pr,
        "title": title,
        "commit_sha": run.commit_sha,
        "status": run.status,
        "error": run.error,
        "llm_requests": run.llm_requests,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "est_cost_usd": float(run.est_cost_usd),
        "created_at": run.created_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


async def _owned_run(db, session: Session, run_id: int):
    row = (await db.execute(_my_runs(session).where(Run.id == run_id))).first()
    if row is None:
        raise HTTPException(404, "Run not found")
    return row


@router.get("/api/runs")
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    cursor: int | None = Query(None, ge=1),
    status: str | None = Query(None, max_length=32),
    session: Session = Depends(get_session),
    db=Depends(get_db),
):
    posted = (
        select(func.count())
        .where(Finding.run_id == Run.id, Finding.status == "posted")
        .scalar_subquery()
    )
    query = _my_runs(session).add_columns(posted).order_by(Run.id.desc()).limit(limit + 1)
    if cursor:
        query = query.where(Run.id < cursor)  # keyset pagination: no OFFSET scans
    if status:
        query = query.where(Run.status == status)
    rows = (await db.execute(query)).all()
    items = [_run_json(r[0], r[1], r[2], r[3]) | {"findings": r[4]} for r in rows[:limit]]
    return {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None}


@router.get("/api/runs/{run_id}")
async def get_run(run_id: int, session: Session = Depends(get_session), db=Depends(get_db)):
    run, repo, pr, title = await _owned_run(db, session, run_id)
    rows = await db.execute(
        select(Finding, Feedback.verdict)
        .outerjoin(
            Feedback,
            (Feedback.finding_id == Finding.id) & (Feedback.github_user_id == session.user_id),
        )
        .where(Finding.run_id == run.id)
        .order_by(Finding.file, Finding.line)
    )
    findings = [
        {
            "id": f.id,
            "file": f.file,
            "line": f.line,
            "category": f.category,
            "severity": f.severity,
            "confidence": float(f.confidence),
            "explanation": f.explanation,  # LLM text: the UI renders it as plain text only
            "status": f.status,
            "my_verdict": verdict,
        }
        for f, verdict in rows
    ]
    return _run_json(run, repo, pr, title) | {"findings": findings}


@router.get("/api/runs/{run_id}/trace")
async def get_trace(run_id: int, session: Session = Depends(get_session), db=Depends(get_db)):
    await _owned_run(db, session, run_id)
    steps = await db.scalars(
        select(TraceStep).where(TraceStep.run_id == run_id).order_by(TraceStep.step_no)
    )
    return [
        {
            "step_no": t.step_no,
            "tool": t.tool,
            "summary": t.summary,
            "tokens_in": t.tokens_in,
            "tokens_out": t.tokens_out,
            "duration_ms": t.duration_ms,
        }
        for t in steps
    ]
