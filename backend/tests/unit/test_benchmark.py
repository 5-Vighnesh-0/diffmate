import json

import pytest
from benchmark import corpus, runner, score

from app.agent.budget import DailyCap
from app.agent.llm import LlmStep, ToolCall


def label(line, file="m.py", category="bug"):
    return [{"file": file, "line_start": line, "line_end": line, "category": category}]


BEFORE = "a = 1\nb = 2\nc = 3\nd = 4\n"
AFTER = "a = 1\nb = 20\nc = 3\nd = 4\ne = 5\n"


def case(**over):
    base = {
        "name": "01-x-demo",
        "kind": "seeded",
        "split": "dev",
        "source": {"repo": "o/r", "commit": "abc", "license": "MIT"},
        "title": "t",
        "body": "b",
        "before": {"m.py": BEFORE},
        "after": {"m.py": AFTER, "new.py": "x = 1\n"},
        "bugs": [{"file": "m.py", "line_start": 2, "line_end": 2, "category": "bug", "why": "w"}],
    }
    return base | over


# corpus


def test_pr_files_build_github_style_patches_for_modified_and_added_files():
    files = {f.path: f for f in corpus.pr_files(case())}

    assert files["m.py"].status == "modified"
    assert files["m.py"].patch.startswith("@@ -1,4 +1,5 @@")
    assert "-b = 2\n+b = 20" in files["m.py"].patch
    assert files["m.py"].lines == {1, 2, 3, 4, 5}  # changed lines plus context
    assert files["new.py"].status == "added"
    assert files["new.py"].patch == "@@ -0,0 +1 @@\n+x = 1"


def test_changed_lines_are_only_added_or_replaced_lines():
    assert corpus.changed_lines(BEFORE, AFTER) == {2, 5}
    assert corpus.changed_lines(None, "x\ny\n") == {1, 2}


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"kind": "toy"}, "kind"),
        ({"split": "test"}, "split"),
        ({"bugs": []}, "clean"),
        ({"kind": "clean"}, "clean"),
        ({"before": {"gone.py": "x\n"}}, "before"),
        ({"after": {f"f{i}.py": "x\n" for i in range(4)}, "before": {}}, "files"),
        ({"after": {"m.py": "x\n" * 601}, "before": {}}, "600"),
        ({"bugs": label(3)}, "changed"),
        ({"bugs": label(1, "zz.py")}, "changed"),
        ({"bugs": label(2, category="style")}, "category"),
    ],
)
def test_invalid_cases_are_rejected_with_the_case_name(over, message):
    with pytest.raises(ValueError, match=f"01-x-demo: .*{message}"):
        corpus.validate(case(**over))


def test_a_clean_case_without_bugs_is_valid():
    corpus.validate(case(kind="clean", bugs=[]))


def test_load_cases_filters_by_split_and_rejects_duplicate_names(tmp_path):
    for name, split in [("01-a", "dev"), ("02-b", "holdout")]:
        (tmp_path / f"{name}.json").write_text(json.dumps(case(name=name, split=split)))

    assert [c["name"] for c in corpus.load_cases("holdout", tmp_path)] == ["02-b"]
    assert len(corpus.load_cases(None, tmp_path)) == 2

    (tmp_path / "03-dup.json").write_text(json.dumps(case(name="01-a")))
    with pytest.raises(ValueError, match="duplicate"):
        corpus.load_cases(None, tmp_path)


def test_case_set_sha_is_stable_and_changes_with_any_case():
    a = corpus.case_set_sha([case(name="1"), case(name="2")])

    assert a == corpus.case_set_sha([case(name="2"), case(name="1")])
    assert a != corpus.case_set_sha([case(name="1"), case(name="2", title="other")])
    assert len(a) == 12


# score

BUG = {"file": "m.py", "line_start": 10, "line_end": 12}


def f(line, file="m.py"):
    return {"file": file, "line": line}


def test_a_finding_within_3_lines_of_the_label_is_a_hit_and_outside_is_a_false_positive():
    assert score.match([f(7), f(15)], [BUG]) == (1, 0)
    assert score.match([f(6)], [BUG]) == (0, 1)
    assert score.match([f(16)], [BUG]) == (0, 1)
    assert score.match([f(11, "other.py")], [BUG]) == (0, 1)


def test_a_label_counts_once_and_extra_findings_on_it_are_not_false_positives():
    assert score.match([f(10), f(11), f(12)], [BUG]) == (1, 0)


def test_every_finding_on_a_clean_case_is_a_false_positive():
    assert score.match([f(1), f(2)], []) == (0, 2)


def row(name, bugs, findings, seconds=10.0, cost=0.01, kind="seeded"):
    return {
        "name": name,
        "kind": kind,
        "bugs": bugs,
        "seconds": seconds,
        "linter_seconds": 1.0,
        "cost_usd": cost,
        "setups": {"linter": [], "agent": findings, "filtered": findings},
    }


def test_summarize_computes_every_metric():
    rows = [
        row("a", [BUG], [f(10), f(40)], seconds=10),  # 1 hit, 1 FP
        row("b", [BUG], [], seconds=20),  # miss
        row("c", [], [f(3)], seconds=30, kind="clean"),  # FP
        row("d", [BUG], [f(11)], seconds=40),  # hit
    ]

    s = score.summarize(rows, "filtered")

    assert s["cases"] == 4
    assert s["precision"] == pytest.approx(2 / 4)
    assert s["recall"] == pytest.approx(2 / 3)
    assert s["fp_per_pr"] == pytest.approx(2 / 4)
    assert s["cost_per_pr"] == pytest.approx(0.01)
    assert (s["p50"], s["p95"]) == (20, 40)


def test_linter_setup_uses_linter_time_and_costs_nothing_and_no_findings_means_no_precision():
    s = score.summarize([row("a", [BUG], [])], "linter")

    assert s["precision"] is None
    assert s["cost_per_pr"] == 0
    assert s["p50"] == 1.0


def test_table_renders_one_row_per_setup_with_na_for_missing_precision():
    s = score.summarize([row("a", [BUG], [])], "linter")
    text = score.table({"linter": s})

    assert "| 1. Linter only | n/a | 0% | 0.00 | $0.0000 | 1.0 s | 1.0 s |" in text


def test_write_between_markers_replaces_only_the_marked_block(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("top\n<!-- bench:dev -->\nold\n<!-- /bench:dev -->\nbottom\n")

    score.write_between_markers(doc, "dev", "new table")

    assert doc.read_text() == "top\n<!-- bench:dev -->\nnew table\n<!-- /bench:dev -->\nbottom\n"


# runner


class FakeLLM:
    def __init__(self, script):
        self.script, self.calls = script, 0

    async def step(self, system, history, tools, max_output_tokens):
        name, args = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        call = ToolCall(id=f"c{self.calls}", name=name, arguments=args)
        return LlmStep([call], "", 1_000, 100, [{"type": "function_call", "id": call.id}])


class Counter:
    def __init__(self):
        self.n = 0

    async def set(self, *args, **kwargs):
        return None

    async def incr(self, key):
        self.n += 1
        return self.n


def submit(*findings):
    return ("submit_findings", {"findings": list(findings)})


def finding(line, confidence=0.9, file="m.py"):
    return {
        "file": file,
        "line": line,
        "category": "bug",
        "severity": "high",
        "confidence": confidence,
        "explanation": "wrong value",
    }


async def test_one_agent_run_feeds_the_agent_and_filtered_setups():
    llm = FakeLLM([submit(finding(2), finding(2, confidence=0.3), finding(40))])

    r = await runner.bench_case(case(), llm, DailyCap(Counter(), 10), "gemini-3.5-flash-lite")

    assert llm.calls == 1
    assert [x["line"] for x in r["setups"]["agent"]] == [2, 2, 40]
    assert [x["line"] for x in r["setups"]["filtered"]] == [2]  # low confidence, not in diff
    assert r["bugs"] == case()["bugs"]
    assert r["stop_reason"] == "submitted"
    assert r["cost_usd"] > 0


async def test_linter_hints_only_on_lines_in_the_diff_become_linter_findings():
    c = case(
        before={"m.py": "import os\n" + BEFORE},
        after={"m.py": "import os\n" + BEFORE + "import sys\n"},
        bugs=label(6),
    )
    r = await runner.bench_case(c, FakeLLM([submit()]), DailyCap(Counter(), 10), "m")

    linter = r["setups"]["linter"]
    assert {x["line"] for x in linter} == {6}  # unused `sys`; unused `os` (line 1) is not in diff
    assert any(x["explanation"].startswith("F401") for x in linter)


async def test_bench_resumes_and_stops_cleanly_at_the_daily_cap(tmp_path):
    cases = [case(name=f"0{i}-x") for i in range(1, 4)]
    out = tmp_path / "r.jsonl"
    out.write_text(json.dumps({"name": "01-x"}) + "\n")  # finished on an earlier day
    llm = FakeLLM([submit(finding(2))])

    code = await runner.bench(cases, llm, DailyCap(Counter(), 1), "m", out)

    assert code == 3  # stopped: cap reached during case 03
    assert [json.loads(line)["name"] for line in out.read_text().splitlines()] == ["01-x", "02-x"]


def test_long_files_diff_minimally_like_github():
    # difflib's default "autojunk" heuristic misaligned this 400-line file: one rewritten
    # method showed the untouched class below it as deleted and re-added (35 lines, not 12).
    c = json.loads((corpus.CASES / "03-httpx-bytechunker-remainder.json").read_text())
    path = "httpx/_decoders.py"

    assert len(corpus.changed_lines(c["before"][path], c["after"][path])) == 12
    assert "class TextChunker" not in corpus.patch(c["before"][path], c["after"][path])
