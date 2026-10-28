import pytest
from pydantic import ValidationError

from app.agent.filters import filter_findings
from app.agent.schemas import Finding

DIFF = {"a.py": set(range(1, 101))}


def f(line=10, confidence=0.9, severity="high", category="bug", file="a.py") -> Finding:
    return Finding(
        file=file,
        line=line,
        category=category,
        severity=severity,
        confidence=confidence,
        explanation="x",
    )


def statuses(results):
    return [(r[0].line, r[1]) for r in results]


def test_schema_rejects_unknown_fields_and_out_of_range_values():
    with pytest.raises(ValidationError):
        Finding.model_validate({**f().model_dump(), "post_as_admin": True})
    with pytest.raises(ValidationError):
        Finding.model_validate({**f().model_dump(), "confidence": 1.5})
    with pytest.raises(ValidationError):
        Finding.model_validate({**f().model_dump(), "category": "style"})


def test_lines_outside_the_diff_are_dropped():
    assert statuses(filter_findings([f(line=500), f(file="b.py")], DIFF)) == [
        (500, "dropped_not_in_diff"),
        (10, "dropped_not_in_diff"),
    ]


def test_low_confidence_is_dropped():
    assert statuses(filter_findings([f(confidence=0.69)], DIFF)) == [(10, "dropped_low_confidence")]


def test_near_duplicates_keep_the_more_confident_one():
    results = filter_findings([f(line=10, confidence=0.8), f(line=12, confidence=0.95)], DIFF)

    assert statuses(results) == [(12, "posted"), (10, "dropped_duplicate")]


def test_same_place_different_category_is_not_a_duplicate():
    results = filter_findings([f(category="bug"), f(category="security")], DIFF)

    assert [s for _, s in results] == ["posted", "posted"]


def test_keeps_five_ordered_by_severity_then_confidence():
    findings = [f(line=n * 10, severity="low", confidence=0.99) for n in range(1, 5)] + [
        f(line=60, severity="high", confidence=0.8),
        f(line=70, severity="medium", confidence=0.9),
        f(line=80, severity="high", confidence=0.95),
    ]

    results = filter_findings(findings, DIFF)

    posted = [r[0].line for r in results if r[1] == "posted"]
    assert posted == [80, 60, 70, 10, 20]
    assert sum(1 for r in results if r[1] == "dropped_over_cap") == 2


def test_a_stricter_category_needs_the_higher_bar():
    results = filter_findings(
        [
            f(line=10, confidence=0.8),
            f(line=30, confidence=0.95),
            f(line=50, confidence=0.8, category="security"),
        ],
        DIFF,
        stricter={"bug"},
        strict_threshold=0.9,
    )
    assert sorted(statuses(results)) == [(10, "dropped_stricter"), (30, "posted"), (50, "posted")]


def test_below_the_normal_bar_is_still_low_confidence_in_a_stricter_category():
    results = filter_findings([f(confidence=0.5)], DIFF, stricter={"bug"}, strict_threshold=0.9)
    assert statuses(results) == [(10, "dropped_low_confidence")]


def test_a_fix_cannot_break_out_of_its_code_block_or_run_long():
    for bad in ["x = 1\n```\n![x](https://evil.example)", "~~~", "\n".join(["x = 1"] * 11)]:
        with pytest.raises(ValidationError):
            Finding.model_validate({**f().model_dump(), "fix": bad})
    assert Finding.model_validate({**f().model_dump(), "fix": "x = 1\ny = 2"}).fix == "x = 1\ny = 2"
