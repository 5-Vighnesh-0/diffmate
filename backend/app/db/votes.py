"""Learn from votes: a category gets a stricter bar in a repo whose people mostly voted it
Not useful (at least 3 votes, at least 2 of every 3 Not useful). It only ever raises the bar,
and it lowers again by itself when later votes stop meeting the rule."""

from dataclasses import dataclass

from sqlalchemy import func, select

from app.db.models import Feedback, Finding, PullRequest, Run

MIN_VOTES = 3


@dataclass(frozen=True)
class CategoryVotes:
    category: str
    not_useful: int
    total: int


async def stricter_categories(s, repo_ids) -> dict[int, list[CategoryVotes]]:
    """Stricter categories per repo id (repos.id), with the votes behind them."""
    if not repo_ids:
        return {}
    total = func.count()
    not_useful = func.count().filter(Feedback.verdict == "reject")
    rows = await s.execute(
        select(PullRequest.repo_id, Finding.category, not_useful, total)
        .select_from(Feedback)
        .join(Finding, Finding.id == Feedback.finding_id)
        .join(Run, Run.id == Finding.run_id)
        .join(PullRequest, PullRequest.id == Run.pull_request_id)
        .where(PullRequest.repo_id.in_(repo_ids))
        .group_by(PullRequest.repo_id, Finding.category)
        .having(total >= MIN_VOTES, not_useful * 3 >= total * 2)
        .order_by(PullRequest.repo_id, Finding.category)
    )
    out: dict[int, list[CategoryVotes]] = {}
    for repo_id, category, rejected, count in rows:
        out.setdefault(repo_id, []).append(CategoryVotes(category, rejected, count))
    return out
