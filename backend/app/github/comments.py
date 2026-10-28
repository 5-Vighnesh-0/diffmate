import re

import httpx

from app.agent.schemas import Finding

LABELS = {"bug": "Bug", "security": "Security", "missing_test": "Missing test"}
MARKDOWN_SPECIALS = re.compile(r"([\\`*_\[\]()!#|~])")


def plain(text: str) -> str:
    """Model text is shown as plain text: no HTML, links, images, URLs, or @-mentions."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = MARKDOWN_SPECIALS.sub(r"\\\1", text)
    text = text.replace("@", "@\N{ZERO WIDTH SPACE}")  # zero-width space: no pings
    text = text.replace("://", ":\N{ZERO WIDTH SPACE}//")  # no auto-linked URLs
    return " ".join(text.split())


SUGGEST_MIN_CONFIDENCE = 0.95  # one-click fixes only on the surest notes


def format_comment(f: Finding) -> str:
    percent = round(f.confidence * 100)
    head = f"**{LABELS[f.category]}** · {f.severity} severity · {percent}% confidence"
    body = f"{head}\n\n{plain(f.explanation)}"
    if f.fix and f.confidence >= SUGGEST_MIN_CONFIDENCE:
        # Inside a fence nothing renders; the schema forbids fences in the fix itself.
        body += f"\n\nSuggested fix (check it before committing):\n```suggestion\n{f.fix}\n```"
    return body


def marker(sha: str) -> str:
    return f"<!-- diffmate:{sha} -->"


async def post_review(
    http: httpx.AsyncClient, token: str, repo: str, pr: int, sha: str, findings: list[Finding]
) -> int | None:
    """Post one COMMENT review with inline comments; its id, or None if nothing to post or
    already posted."""
    if not findings:
        return None
    auth = {"Authorization": f"Bearer {token}"}
    r = await http.get(f"/repos/{repo}/pulls/{pr}/reviews", params={"per_page": 100}, headers=auth)
    r.raise_for_status()
    # Only a bot can have posted our marker: a PR author pasting it must not suppress the review.
    if any(
        marker(sha) in (review.get("body") or "")
        and (review.get("user") or {}).get("type") == "Bot"
        for review in r.json()
    ):
        return None  # a previous try already posted this commit's review

    noun = "finding" if len(findings) == 1 else "findings"
    body = f"DiffMate reviewed `{sha[:7]}`: {len(findings)} {noun}.\n\n{marker(sha)}"
    comments = [
        {"path": f.file, "line": f.line, "side": "RIGHT", "body": format_comment(f)}
        for f in findings
    ]
    r = await http.post(
        f"/repos/{repo}/pulls/{pr}/reviews",
        headers=auth,
        json={"commit_id": sha, "event": "COMMENT", "body": body, "comments": comments},
    )
    r.raise_for_status()
    return r.json()["id"]


async def review_comment_ids(
    http: httpx.AsyncClient, token: str, repo: str, pr: int, review_id: int
) -> dict[tuple[str, int, str], int]:
    """GitHub's id for each inline comment of a review, by (file, line, body): replies point
    to it. The body tells apart two notes on the same line."""
    r = await http.get(
        f"/repos/{repo}/pulls/{pr}/reviews/{review_id}/comments",
        params={"per_page": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return {(c["path"], c["line"], c["body"]): c["id"] for c in r.json() if c.get("line")}


async def reply_to_comment(
    http: httpx.AsyncClient, token: str, repo: str, pr: int, comment_id: int, text: str
) -> None:
    r = await http.post(
        f"/repos/{repo}/pulls/{pr}/comments/{comment_id}/replies",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": plain(text)},
    )
    r.raise_for_status()


async def withdraw_comment(
    http: httpx.AsyncClient, token: str, repo: str, comment_id: int, explanation: str
) -> None:
    """Strike through DiffMate's own note after it agreed it was wrong."""
    body = f"**Withdrawn:** DiffMate agreed this note was wrong.\n\n~~{plain(explanation)}~~"
    r = await http.patch(
        f"/repos/{repo}/pulls/comments/{comment_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": body},
    )
    r.raise_for_status()
