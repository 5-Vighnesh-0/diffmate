"""Load, validate, and diff the offline benchmark cases. Format: docs/benchmark.md."""

import difflib
import hashlib
import json
from pathlib import Path

from app.github.diff import PrFile, parse_patch

CASES = Path(__file__).parent / "cases"
KINDS = {"seeded", "real", "clean"}
SPLITS = {"dev", "holdout"}
CATEGORIES = {"bug", "security", "missing_test"}
REQUIRED = {"name", "kind", "split", "source", "title", "body", "before", "after", "bugs"}
MAX_FILES = 3
MAX_LINES = 600


def _matcher(before: str | None, after: str) -> difflib.SequenceMatcher:
    # autojunk off: its speed heuristic misaligns files over 200 lines (see test).
    return difflib.SequenceMatcher(
        None, (before or "").splitlines(), after.splitlines(), autojunk=False
    )


def _range(start: int, stop: int) -> str:
    length = stop - start
    first = start + 1 if length else start  # an empty range names the line before it
    return str(first) if length == 1 else f"{first},{length}"


def patch(before: str | None, after: str) -> str:
    """A GitHub-style patch (hunks only, 3 context lines) from before to after."""
    matcher = _matcher(before, after)
    a, b = matcher.a, matcher.b
    out = []
    for group in matcher.get_grouped_opcodes(3):
        (_, i1, _, j1, _), (_, _, i2, _, j2) = group[0], group[-1]
        out.append(f"@@ -{_range(i1, i2)} +{_range(j1, j2)} @@")
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                out += [" " + line for line in a[i1:i2]]
            else:
                out += ["-" + line for line in a[i1:i2]] + ["+" + line for line in b[j1:j2]]
    return "\n".join(out)


def changed_lines(before: str | None, after: str) -> set[int]:
    """New-side line numbers that were added or replaced."""
    return {
        n + 1
        for tag, _, _, j1, j2 in _matcher(before, after).get_opcodes()
        if tag in ("replace", "insert")
        for n in range(j1, j2)
    }


def pr_files(case: dict) -> list[PrFile]:
    files = []
    for path, after in case["after"].items():
        before = case["before"].get(path)
        p = patch(before, after)
        files.append(PrFile(path, "added" if before is None else "modified", p, parse_patch(p)))
    return files


def validate(case: dict) -> None:
    name = case.get("name", "?")

    def bad(message: str):
        raise ValueError(f"{name}: {message}")

    if missing := REQUIRED - case.keys():
        bad(f"missing keys {sorted(missing)}")
    if case["kind"] not in KINDS:
        bad(f"kind must be one of {sorted(KINDS)}")
    if case["split"] not in SPLITS:
        bad(f"split must be one of {sorted(SPLITS)}")
    before, after = case["before"], case["after"]
    if not 1 <= len(after) <= MAX_FILES:
        bad(f"needs 1 to {MAX_FILES} files")
    if set(before) - set(after):
        bad("every file in before must be in after")
    if any(len(text.splitlines()) > MAX_LINES for text in [*before.values(), *after.values()]):
        bad(f"files must have at most {MAX_LINES} lines")
    if (case["kind"] == "clean") != (not case["bugs"]):
        bad("clean cases have no bugs, other kinds at least one")
    for bug in case["bugs"]:
        if bug.get("category") not in CATEGORIES:
            bad(f"bug category must be one of {sorted(CATEGORIES)}")
        file = bug.get("file")
        changed = changed_lines(before.get(file), after[file]) if file in after else set()
        if not changed & set(range(bug["line_start"], bug["line_end"] + 1)):
            bad(f"label {file}:{bug['line_start']} is not on a changed line")


def load_cases(split: str | None = None, folder: Path = CASES) -> list[dict]:
    cases = [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]
    seen = set()
    for case in cases:
        validate(case)
        if case["name"] in seen:
            raise ValueError(f"{case['name']}: duplicate name")
        seen.add(case["name"])
    return [c for c in cases if split is None or c["split"] == split]


def case_set_sha(cases: list[dict]) -> str:
    """Fingerprint of a frozen case set; stamped into every results file name."""
    digest = hashlib.sha256()
    for case in sorted(cases, key=lambda c: c["name"]):
        digest.update(json.dumps(case, sort_keys=True).encode())
    return digest.hexdigest()[:12]
