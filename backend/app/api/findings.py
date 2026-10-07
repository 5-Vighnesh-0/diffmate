from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import get_db, require_csrf
from app.core.sessions import Session
from app.db.models import Feedback, Finding, Installation, PullRequest, Repo, Run

router = APIRouter()


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
    owned = await db.scalar(
        select(Finding.id)
        .join(Run, Run.id == Finding.run_id)
        .join(PullRequest, PullRequest.id == Run.pull_request_id)
        .join(Repo, Repo.id == PullRequest.repo_id)
        .join(Installation, Installation.id == Repo.installation_id)
        .where(
            Finding.id == finding_id,
            Installation.github_installation_id.in_(session.installation_ids),
            Repo.github_repo_id.in_(session.repo_ids),
        )
    )
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
