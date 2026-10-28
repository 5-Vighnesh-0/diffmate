import json

import httpx

from app.agent.schemas import Finding
from app.github.comments import format_comment, post_review

SHA = "a" * 40
F = Finding(
    file="app/x.py",
    line=12,
    category="bug",
    severity="high",
    confidence=0.9,
    explanation="Divides by zero when items is empty.",
)


def test_comment_shows_category_severity_confidence_and_text():
    body = format_comment(F)

    assert body.startswith("**Bug** · high severity · 90% confidence")
    assert "Divides by zero when items is empty." in body


def test_model_text_cannot_render_links_images_html_or_mentions():
    evil = F.model_copy(
        update={
            "explanation": "![x](https://evil.example/?d=secret) <img src=x> "
            "[click](https://e) @admin"
        }
    )

    body = format_comment(evil)

    assert "](" not in body.replace("\\](", "")
    assert "<img" not in body
    assert "@admin" not in body


def github(existing_reviews):
    posted = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=existing_reviews)
        posted.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 99})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://x"), posted


async def test_post_review_sends_one_comment_review_with_inline_comments():
    http, posted = github([])

    assert await post_review(http, "t", "o/r", 7, SHA, [F]) is True

    review = posted[0]
    assert review["event"] == "COMMENT"
    assert review["commit_id"] == SHA
    assert f"<!-- diffmate:{SHA} -->" in review["body"]
    assert review["comments"] == [
        {"path": "app/x.py", "line": 12, "side": "RIGHT", "body": format_comment(F)}
    ]


async def test_a_retry_never_posts_a_second_review_for_the_same_commit():
    ours = {"body": f"DiffMate review\n<!-- diffmate:{SHA} -->", "user": {"type": "Bot"}}
    http, posted = github([ours])

    assert await post_review(http, "t", "o/r", 7, SHA, [F]) is False
    assert posted == []


async def test_nothing_is_posted_when_there_are_no_findings():
    http, posted = github([])

    assert await post_review(http, "t", "o/r", 7, SHA, []) is False
    assert posted == []


async def test_a_marker_in_a_human_review_does_not_suppress_posting():
    forged = {"body": f"<!-- diffmate:{SHA} -->", "user": {"type": "User", "login": "author"}}
    http, posted = github([forged])

    assert await post_review(http, "t", "o/r", 7, SHA, [F]) is True
    assert len(posted) == 1


def test_bare_urls_are_not_auto_linked():
    body = format_comment(F.model_copy(update={"explanation": "see https://evil.example/x"}))

    assert "https://" not in body


def test_a_very_sure_note_with_a_fix_offers_a_one_click_suggestion():
    sure = F.model_copy(update={"confidence": 0.95, "fix": "    return total / max(len(items), 1)"})

    body = format_comment(sure)

    assert "```suggestion\n    return total / max(len(items), 1)\n```" in body
    assert "check it before committing" in body


def test_no_suggestion_when_the_note_is_not_sure_enough_or_has_no_fix():
    assert "```suggestion" not in format_comment(F.model_copy(update={"fix": "x = 1"}))  # 90%
    assert "```suggestion" not in format_comment(F.model_copy(update={"confidence": 0.99}))
