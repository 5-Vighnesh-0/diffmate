"""Learn from votes: a category gets a stricter bar where people mostly voted it Not useful."""

from app.db.models import Feedback, Finding, Installation, PullRequest, Repo, Run
from app.db.votes import CategoryVotes, stricter_categories


async def repo_with_votes(s, github_repo_id, votes, category="bug"):
    """One repo; one finding per vote, so each vote is on its own note."""
    repo = Repo(
        installation=Installation(github_installation_id=github_repo_id, account_login="o"),
        github_repo_id=github_repo_id,
        full_name=f"o/r{github_repo_id}",
    )
    pr = PullRequest(repo=repo, number=1, title="t")
    s.add(pr)
    await s.flush()
    run = Run(pull_request_id=pr.id, commit_sha="a" * 40, status="done")
    s.add(run)
    await s.flush()
    for i, verdict in enumerate(votes):
        finding = Finding(
            run_id=run.id,
            source="agent",
            file="a.py",
            line=i + 1,
            category=category,
            severity="low",
            confidence=0.8,
            explanation="x",
            status="posted",
        )
        s.add(finding)
        await s.flush()
        s.add(Feedback(finding_id=finding.id, github_user_id=7, verdict=verdict))
    await s.commit()
    return repo.id


async def test_two_votes_are_never_enough(session):
    repo = await repo_with_votes(session, 1, ["reject", "reject"])
    assert await stricter_categories(session, [repo]) == {}


async def test_three_votes_two_not_useful_make_the_category_stricter(session):
    repo = await repo_with_votes(session, 1, ["reject", "reject", "accept"])
    assert await stricter_categories(session, [repo]) == {repo: [CategoryVotes("bug", 2, 3)]}


async def test_mostly_useful_or_under_two_thirds_is_not_stricter(session):
    one_of_three = await repo_with_votes(session, 1, ["reject", "accept", "accept"])
    three_of_five = await repo_with_votes(
        session, 2, ["reject", "reject", "reject", "accept", "accept"]
    )
    assert await stricter_categories(session, [one_of_three, three_of_five]) == {}


async def test_votes_count_only_for_their_own_repo_and_category(session):
    mine = await repo_with_votes(session, 1, ["accept"])
    await repo_with_votes(session, 2, ["reject", "reject", "reject"])
    assert await stricter_categories(session, [mine]) == {}


async def test_the_bar_goes_back_down_when_later_votes_are_useful(session):
    repo = await repo_with_votes(session, 1, ["reject", "reject", "reject"])
    assert repo in await stricter_categories(session, [repo])
    run_id = (await session.get(Finding, 1)).run_id
    for line in (10, 11):
        finding = Finding(
            run_id=run_id,
            source="agent",
            file="a.py",
            line=line,
            category="bug",
            severity="low",
            confidence=0.8,
            explanation="x",
            status="posted",
        )
        session.add(finding)
        await session.flush()
        session.add(Feedback(finding_id=finding.id, github_user_id=7, verdict="accept"))
    await session.commit()
    assert await stricter_categories(session, [repo]) == {}  # 3 of 5: below two thirds
