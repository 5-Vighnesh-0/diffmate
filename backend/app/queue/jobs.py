def review_job_id(repo: str, pr: int, sha: str) -> str:
    return f"review:{repo}:{pr}:{sha}"


async def enqueue_review(pool, *, repo: str, pr: int, sha: str, installation_id: int) -> bool:
    """Queue one review per commit. arq refuses a second job with the same ID -> returns False."""
    job = await pool.enqueue_job(
        "review_pr", repo, pr, sha, installation_id, _job_id=review_job_id(repo, pr, sha)
    )
    return job is not None
