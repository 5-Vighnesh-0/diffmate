"""Score benchmark results and write the table into the docs.

    make bench-score FILE=benchmark/results/<file>.jsonl  # prints the table, writes the docs

Matching rule and metrics: docs/benchmark.md."""

import argparse
import json
import math
import re
from pathlib import Path

TOLERANCE = 3
SETUPS = {"linter": "1. Linter only", "agent": "2. Agent only", "filtered": "3. Agent + filtering"}
ROOT = Path(__file__).parent.parent
DOCS = [ROOT / "docs" / "benchmark.md", ROOT / "README.md"]
LANDING_JSON = ROOT / "frontend" / "src" / "lib" / "benchmark.json"  # bundled by the landing page


def _hits(finding: dict, bug: dict, tolerance: int) -> bool:
    return (
        finding["file"] == bug["file"]
        and bug["line_start"] - tolerance <= finding["line"] <= bug["line_end"] + tolerance
    )


def match(findings: list[dict], bugs: list[dict], tolerance: int = TOLERANCE) -> tuple[int, int]:
    """(labels found, findings matching no label). Extra findings on a found label count as
    neither, so one bug reported twice is not a false positive."""
    found = sum(any(_hits(f, b, tolerance) for f in findings) for b in bugs)
    unmatched = sum(not any(_hits(f, b, tolerance) for b in bugs) for f in findings)
    return found, unmatched


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[max(math.ceil(p * len(ordered)) - 1, 0)]  # nearest rank


def summarize(rows: list[dict], setup: str) -> dict:
    found = unmatched = labels = 0
    for r in rows:
        f, u = match(r["setups"][setup], r["bugs"])
        found, unmatched, labels = found + f, unmatched + u, labels + len(r["bugs"])
    linter = setup == "linter"
    seconds = [r["linter_seconds"] if linter else r["seconds"] for r in rows]
    return {
        "cases": len(rows),
        "precision": found / (found + unmatched) if found + unmatched else None,
        "recall": found / labels if labels else None,
        "fp_per_pr": unmatched / len(rows),
        "cost_per_pr": 0.0 if linter else sum(r["cost_usd"] for r in rows) / len(rows),
        "p50": _percentile(seconds, 0.5),
        "p95": _percentile(seconds, 0.95),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def table(summaries: dict[str, dict]) -> str:
    lines = [
        "| Setup | Precision | Recall | FP / PR | Est. cost / PR | p50 | p95 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for setup, s in summaries.items():
        lines.append(
            f"| {SETUPS[setup]} | {_pct(s['precision'])} | {_pct(s['recall'])} "
            f"| {s['fp_per_pr']:.2f} | ${s['cost_per_pr']:.4f} "
            f"| {s['p50']:.1f} s | {s['p95']:.1f} s |"
        )
    return "\n".join(lines)


def write_between_markers(doc: Path, key: str, text: str) -> None:
    pattern = re.compile(rf"(<!-- bench:{key} -->\n).*?(\n<!-- /bench:{key} -->)", re.S)
    content = doc.read_text()
    if not pattern.search(content):
        raise ValueError(f"{doc.name}: no <!-- bench:{key} --> markers")
    doc.write_text(pattern.sub(lambda m: m[1] + text + m[2], content))


def report(path: Path) -> tuple[str, str, dict]:
    """(marker key, Markdown, summaries) for one results file, e.g. dev-<model>-<sha>.jsonl."""
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    split, rest = path.stem.split("-", 1)
    model, sha = rest.rsplit("-", 1)
    summaries = {setup: summarize(rows, setup) for setup in SETUPS}
    text = table(summaries)
    requests = sum(r["llm_requests"] for r in rows)
    note = (
        f"\n\n{len(rows)} cases ({split}), `{model}`, case set `{sha}`, {requests} requests. "
        "Cost is estimated at list price; the free tier costs $0."
    )
    key = split if model == "gemini-3.5-flash-lite" else f"{split}-{model}"
    entry = {"cases": len(rows), "model": model, "case_set": sha, "setups": summaries}
    return key, text + note, entry


def write_json(path: Path, key: str, entry: dict) -> None:
    data = json.loads(path.read_text()) if path.exists() else {}
    path.write_text(json.dumps(data | {key: entry}, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--write", action="store_true", help="update docs/benchmark.md and README")
    args = parser.parse_args()
    key, text, entry = report(args.results)
    print(text)
    if args.write:
        for doc in DOCS:
            if f"<!-- bench:{key} -->" in doc.read_text():
                write_between_markers(doc, key, text)
                print(f"updated {doc.relative_to(ROOT)}")
        write_json(LANDING_JSON, key, entry)
        print(f"updated {LANDING_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
