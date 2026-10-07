"""An LLM that fully 'obeys' a prompt injection still cannot make DiffMate misbehave:
the code enforces the tool list, the diff-only rule, the 5-comment cap and plain-text output."""

from tests.integration.test_pipeline import SHA, FakeLLM, ctx, review_pr


def finding(line, text="x", file="calc.py"):
    return {
        "file": file,
        "line": line,
        "category": "bug",
        "severity": "high",
        "confidence": 0.99,
        "explanation": text,
    }


async def test_an_obedient_model_still_cannot_escape_the_guardrails(sessionmaker):
    flood = [finding(n % 3 + 1) for n in range(50)]  # 50 findings on 3 diff lines
    obedient = FakeLLM(
        [
            ("approve_pull_request", {"event": "APPROVE"}),
            ("read_file", {"path": "../../../../etc/passwd"}),
            (
                "submit_findings",
                {
                    "findings": [
                        finding(999, "LGTM"),
                        finding(2, "[click me](https://evil.example) <img src=x> @admin"),
                        finding(1, "ok", file="../../etc/passwd"),
                        *flood,
                    ]
                },
            ),
        ]
    )
    reviews = []

    await review_pr(ctx(sessionmaker, obedient, reviews), "o/r", 7, SHA, 42)

    comments = reviews[0]["comments"]
    assert len(reviews) == 1 and len(comments) <= 5
    assert all(c["path"] == "calc.py" and c["line"] in {1, 2, 3} for c in comments)
    bodies = " ".join(c["body"] for c in comments)
    assert "](" not in bodies.replace("\\](", "")
    assert "<img" not in bodies and "@admin" not in bodies and "https://" not in bodies
    assert reviews[0]["event"] == "COMMENT"  # never APPROVE or REQUEST_CHANGES
