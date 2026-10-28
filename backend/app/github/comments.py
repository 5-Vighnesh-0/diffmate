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
) -> bool:
    """Post one COMMENT review with inline comments. False if nothing to post or already posted."""
    if not findings:
        return False
    auth = {"Authorization": f"Bearer {token}"}
    r = await http.get(f"/repos/{repo}/pulls/{pr}/reviews", params={"per_page": 100}, headers=auth)
    r.raise_for_status()
    # Only a bot can have posted our marker: a PR author pasting it must not suppress the review.
    if any(
        marker(sha) in (review.get("body") or "")
        and (review.get("user") or {}).get("type") == "Bot"
        for review in r.json()
    ):
        return False  # a previous try already posted this commit's review

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
    return True
