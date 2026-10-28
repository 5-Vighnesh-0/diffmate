from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import get_db, get_session, require_csrf
from app.core.sessions import Session
from app.db.models import Feedback, Finding, Installation, PullRequest, Repo, Run
from app.db.votes import stricter_categories

router = APIRouter()


def _mine(query, session: Session):
    """Limit a findings query to repos the signed-in user can access (threat model #19)."""
    return (
        query.join(Run, Run.id == Finding.run_id)
        .join(PullRequest, PullRequest.id == Run.pull_request_id)
        .join(Repo, Repo.id == PullRequest.repo_id)
        .join(Installation, Installation.id == Repo.installation_id)
        .where(
            Installation.github_installation_id.in_(session.installation_ids),
            Repo.github_repo_id.in_(session.repo_ids),
        )
    )


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["accept", "reject"]


@router.post("/api/findings/{finding_id}/feedback", status_code=204)
async def give_feedback(
    finding_id: int,
    body: FeedbackIn,
    session: Session = Depends(require_csrf),
    db=Depends(get_db),
):
    owned = await db.scalar(_mine(select(Finding.id), session).where(Finding.id == finding_id))
    if owned is None:
        raise HTTPException(404, "Finding not found")
    await db.execute(
        insert(Feedback)
        .values(finding_id=finding_id, github_user_id=session.user_id, verdict=body.verdict)
        .on_conflict_do_update(
            index_elements=["finding_id", "github_user_id"],
            set_={"verdict": body.verdict, "created_at": func.now()},
        )
    )
    await db.commit()
    return Response(status_code=204)


@router.get("/api/feedback/summary")
async def feedback_summary(session: Session = Depends(get_session), db=Depends(get_db)):
    """The signed-in user's own votes: DiffMate's real-world score on their code."""
    rows = await db.execute(
        _mine(select(Feedback.verdict, func.count()).select_from(Finding), session)
        .join(Feedback, Feedback.finding_id == Finding.id)
        .where(Feedback.github_user_id == session.user_id)
        .group_by(Feedback.verdict)
    )
    counts = dict(rows.all())
    repos = dict(
        (
            await db.execute(
                select(Repo.id, Repo.full_name)
                .join(Installation, Installation.id == Repo.installation_id)
                .where(
                    Installation.github_installation_id.in_(session.installation_ids),
                    Repo.github_repo_id.in_(session.repo_ids),
                )
            )
        ).all()
    )
    stricter = await stricter_categories(db, list(repos))
    return {
        "useful": counts.get("accept", 0),
        "not_useful": counts.get("reject", 0),
        # categories where everyone's votes made DiffMate stricter, in repos this user can see
        "stricter": [
            {"repo": repos[r], "category": v.category, "not_useful": v.not_useful, "total": v.total}
            for r, votes in stricter.items()
            for v in votes
        ],
    }
