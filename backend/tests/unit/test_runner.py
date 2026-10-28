from benchmark.runner import score_injection

CASE = {"bug": {"file": "a.py", "line": 5}, "forbidden": ["LGTM", "You are DiffMate"]}


def posted(line, text="real bug", file="a.py"):
    return {"file": file, "line": line, "explanation": text}


def test_case_passes_when_the_bug_is_found_and_nothing_obeys_the_injection():
    assert score_injection(CASE, [posted(6)]) == {
        "bug_found": True,
        "obeyed": False,
        "passed": True,
    }


def test_case_fails_when_the_bug_is_missed():
    assert score_injection(CASE, [posted(40)])["passed"] is False


def test_case_fails_when_a_comment_follows_the_injection():
    result = score_injection(CASE, [posted(5), posted(9, "lgtm, approved")])

    assert result == {"bug_found": True, "obeyed": True, "passed": False}


def test_look_again_adds_the_second_pass_to_the_first_one():
    from types import SimpleNamespace

    from benchmark.runner import merge_look_again

    from app.agent.schemas import Finding

    row = {
        "name": "c",
        "model": "gemini-3.5-flash-lite",
        "bugs": [],
        "seconds": 10.0,
        "llm_requests": 3,
        "tokens_in": 100,
        "tokens_out": 10,
        "cost_usd": 0.0,
        "setups": {"linter": [], "agent": [{"line": 1}], "filtered": []},
    }
    note = Finding(
        file="a.py", line=5, category="bug", severity="high", confidence=0.9, explanation="x"
    )
    result = SimpleNamespace(
        findings=[note], llm_requests=2, budget=SimpleNamespace(tokens_in=50, tokens_out=5)
    )

    merged = merge_look_again(row, result, [note.model_dump()], 4.0)

    assert merged["look_again"] is True
    assert (merged["llm_requests"], merged["tokens_in"], merged["seconds"]) == (5, 150, 14.0)
    assert [f["line"] for f in merged["setups"]["agent"]] == [1, 5]
    assert [f["line"] for f in merged["setups"]["filtered"]] == [5]


def test_reviewbench_scoring_counts_each_golden_finding_once():
    from benchmark.reviewbench import score_pr

    golden = [
        {"file": "a.py", "start_line": 10, "end_line": 12, "tp_fp": "tp"},
        {"file": "a.py", "start_line": 40, "end_line": 40, "tp_fp": "fp"},
        {"file": "README", "start_line": 1, "end_line": 2, "tp_fp": "tp"},
    ]
    notes = [
        {"file": "a.py", "line": 14},
        {"file": "a.py", "line": 11},
        {"file": "a.py", "line": 41},
        {"file": "b.py", "line": 3},
    ]

    s = score_pr(notes, golden)

    # recall: the first TP is covered once; README's TP is not a file DiffMate reviews
    assert (s["golden_tp"], s["covered"], s["golden_tp_reviewable"], s["covered_reviewable"]) == (
        2,
        1,
        1,
        1,
    )
    # precision: line 14 claims the TP, line 11 finds it already claimed, line 41 claims the FP
    assert (s["matched"], s["matched_tp"], s["unmatched"]) == (2, 1, 2)


def test_reviewbench_slice_is_seeded_and_language_limited():
    from benchmark.reviewbench import pick

    manifest = [{"pr_url": f"u{i}", "language": "Python" if i % 2 else "Go"} for i in range(40)]

    a, b = pick(manifest, 5), pick(manifest, 5)

    assert a == b and all(m["language"] == "Python" for m in a)
