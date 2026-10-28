from app.agent.schemas import Finding

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
DUPLICATE_LINE_DISTANCE = 3


def filter_findings(
    findings: list[Finding],
    commentable: dict[str, set[int]],
    threshold: float = 0.7,
    cap: int = 5,
    stricter: frozenset[str] | set[str] = frozenset(),
    strict_threshold: float = 0.9,
) -> list[tuple[Finding, str]]:
    """Return every finding with a status: posted first (best first), then the dropped ones."""
    dropped: list[tuple[Finding, str]] = []

    in_diff = []
    for f in findings:
        if f.line in commentable.get(f.file, set()):
            in_diff.append(f)
        else:  # GitHub only accepts review comments on lines in the diff
            dropped.append((f, "dropped_not_in_diff"))

    confident = []
    for f in in_diff:
        if f.confidence < threshold:
            dropped.append((f, "dropped_low_confidence"))
        elif f.category in stricter and f.confidence < strict_threshold:
            # this repo's people mostly voted this category Not useful (app/db/votes.py)
            dropped.append((f, "dropped_stricter"))
        else:
            confident.append(f)

    unique: list[Finding] = []
    for f in sorted(confident, key=lambda f: -f.confidence):
        if any(
            u.file == f.file
            and u.category == f.category
            and abs(u.line - f.line) <= DUPLICATE_LINE_DISTANCE
            for u in unique
        ):
            dropped.append((f, "dropped_duplicate"))
        else:
            unique.append(f)

    ranked = sorted(unique, key=lambda f: (SEVERITY_RANK[f.severity], -f.confidence))
    dropped += [(f, "dropped_over_cap") for f in ranked[cap:]]
    return [(f, "posted") for f in ranked[:cap]] + dropped
