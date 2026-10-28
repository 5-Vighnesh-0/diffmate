def review_job_id(repo: str, pr: int, sha: str) -> str:
    return f"review:{repo}:{pr}:{sha}"


async def enqueue_review(pool, *, repo: str, pr: int, sha: str, installation_id: int) -> bool:
    """Queue one review per commit. arq refuses a second job with the same ID -> returns False."""
    job = await pool.enqueue_job(
        "review_pr", repo, pr, sha, installation_id, _job_id=review_job_id(repo, pr, sha)
    )
    return job is not None


async def enqueue_reply(
    pool,
    *,
    repo: str,
    pr: int,
    installation_id: int,
    root_id: int,
    reply_id: int,
    body: str,
    diff_hunk: str,
    user_id: int,
) -> bool:
    """Queue one answer per reply comment (the reply's id is the job ID)."""
    job = await pool.enqueue_job(
        "answer_reply",
        repo,
        pr,
        installation_id,
        root_id,
        body,
        diff_hunk,
        user_id,
        _job_id=f"reply:{repo}:{reply_id}",
    )
    return job is not None
