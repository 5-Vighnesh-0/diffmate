"""ruff and ESLint on the PR's changed files. Output is only a hint for the agent.

The PR cannot steer the linters: ruff runs --isolated (ignores the repo's config), ESLint uses
DiffMate's bundled config with lookup and inline config disabled. File names come after "--",
so a PR file named like an option (e.g. "--format=x.ts") cannot change linter behaviour.
Both run with an empty environment (no secrets) and a timeout; a crash just means no hints."""

import asyncio
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

RUFF = [sys.executable, "-m", "ruff"]
RUFF_RULES = "F,E9,B,S"  # pyflakes, syntax errors, bugbear, bandit: bug and security signals
ESLINT_DIR = Path(__file__).parent / "eslint"
TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class LintHint:
    file: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} {self.rule} {self.message}"


async def _run(argv: list[str], cwd: Path) -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        return None
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_SECONDS)
    except (TimeoutError, asyncio.CancelledError) as e:
        proc.kill()
        await asyncio.shield(proc.wait())  # reap the child even when the job is cancelled
        if isinstance(e, asyncio.CancelledError):
            raise
        return None
    return out.decode(errors="replace")


def _inside(root: Path, paths: list[str], suffixes: tuple[str, ...]) -> list[str]:
    root = root.resolve()
    keep = []
    for p in paths:
        try:
            full = (root / p).resolve()
        except (OSError, RuntimeError):  # e.g. a symlink loop
            continue
        if p.endswith(suffixes) and full.is_relative_to(root) and full.is_file():
            keep.append(full.relative_to(root).as_posix())
    return keep


def _rel(root: Path, filename: str) -> str:
    return Path(filename).resolve().relative_to(root.resolve()).as_posix()


async def run_linters(root: Path, paths: list[str]) -> list[LintHint]:
    hints: list[LintHint] = []

    py = _inside(root, paths, (".py",))
    if py:
        argv = [*RUFF, "check", "--isolated", "--no-cache", "--select", RUFF_RULES]
        out = await _run([*argv, "--output-format", "json", "--", *py], root)
        try:
            for d in json.loads(out or "[]"):
                hints.append(
                    LintHint(
                        _rel(root, d["filename"]), d["location"]["row"], d["code"], d["message"]
                    )
                )
        except (ValueError, KeyError, TypeError):
            pass

    ts = _inside(root, paths, (".ts", ".tsx"))
    node = shutil.which("node")
    eslint = ESLINT_DIR / "node_modules" / "eslint" / "bin" / "eslint.js"
    if ts and node and eslint.exists():
        argv = [
            node,
            str(eslint),
            "--no-config-lookup",
            "--config",
            str(ESLINT_DIR / "eslint.config.mjs"),
        ]
        out = await _run([*argv, "--no-inline-config", "--format", "json", "--", *ts], root)
        try:
            for f in json.loads(out or "[]"):
                for m in f["messages"]:
                    rule = m.get("ruleId") or "parse-error"
                    hints.append(
                        LintHint(_rel(root, f["filePath"]), m.get("line", 1), rule, m["message"])
                    )
        except (ValueError, KeyError, TypeError):
            pass

    return hints
