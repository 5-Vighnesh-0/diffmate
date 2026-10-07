import httpx


async def post_issue_comment(
    http: httpx.AsyncClient, token: str, repo: str, pr: int, body: str
) -> None:
    r = await http.post(
        f"/repos/{repo}/issues/{pr}/comments",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": body},
    )
    r.raise_for_status()
