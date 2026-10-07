"""The agent's four tools. All are read-only and confined to the PR's local checkout:
no shell, no network, no writes. Errors come back as text so the model can recover."""

import os
from pathlib import Path

from app.github.diff import PrFile

MAX_LINES = 200
MAX_HITS = 30
MAX_FILE_BYTES = 1_000_000
MAX_LINE_CHARS = 500
MAX_OUTPUT_CHARS = 20_000
MAX_WALK_FILES = 20_000  # a repo with millions of tiny files cannot stall a search
SKIP_DIRS = {"node_modules", "__pycache__", "dist", "build"}


class Tools:
    def __init__(self, root: Path, pr_files: list[PrFile]):
        self.root = root.resolve()
        self.patches = {f.path: f.patch for f in pr_files}

    def _resolve(self, path: str) -> Path | None:
        try:
            target = (self.root / path).resolve()  # follows symlinks, so links out fail too
        except (OSError, RuntimeError):  # e.g. a symlink loop
            return None
        if not target.is_relative_to(self.root) or not target.is_file():
            return None
        if target.stat().st_size > MAX_FILE_BYTES:
            return None
        return target

    def _files(self):
        seen = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(
                d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
            )
            for name in sorted(filenames):
                seen += 1
                if seen > MAX_WALK_FILES:
                    return
                path = Path(dirpath) / name
                if not path.is_symlink() and path.stat().st_size <= MAX_FILE_BYTES:
                    yield path

    def read_file(self, path: str, start_line: int = 1, end_line: int = MAX_LINES) -> str:
        target = self._resolve(path)
        if target is None:
            return "error: file not found, too large, or outside the repository"
        start = max(1, int(start_line))
        end = min(int(end_line), start + MAX_LINES - 1)
        lines = target.read_text(errors="replace").splitlines()[start - 1 : end]
        out = "\n".join(f"{n}: {text[:MAX_LINE_CHARS]}" for n, text in enumerate(lines, start))
        return out[:MAX_OUTPUT_CHARS]

    def search_repo(self, pattern: str) -> str:
        if not 2 <= len(pattern) <= 100:
            return "error: pattern must be 2 to 100 characters"
        hits = []
        for path in self._files():
            rel = path.relative_to(self.root).as_posix()
            for n, text in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if pattern in text:
                    hits.append(f"{rel}:{n}: {text.strip()[:200]}")
                    if len(hits) == MAX_HITS:
                        return "\n".join(hits)
        return "\n".join(hits) or "no matches"

    def view_diff_hunk(self, path: str) -> str:
        if path not in self.patches:
            return "error: file is not part of this pull request"
        return self.patches[path] or "error: diff too large to show"

    def list_related_tests(self, path: str) -> str:
        stem = Path(path).stem
        names = {f"test_{stem}.py", f"{stem}_test.py"} | {
            f"{stem}.{kind}.{ext}" for kind in ("test", "spec") for ext in ("ts", "tsx")
        }
        found = [p.relative_to(self.root).as_posix() for p in self._files() if p.name in names]
        return "\n".join(sorted(found)[:20]) or "no related tests found"

    def call(self, name: str, args: dict) -> str:
        tool = {
            "read_file": self.read_file,
            "search_repo": self.search_repo,
            "view_diff_hunk": self.view_diff_hunk,
            "list_related_tests": self.list_related_tests,
        }.get(name)
        if tool is None:
            return f"error: unknown tool {name!r}"
        try:
            return tool(**args)
        except (TypeError, ValueError):
            return "error: invalid arguments"

    def declarations(self) -> list[dict]:
        def tool(name: str, description: str, props: dict, required: list[str]) -> dict:
            schema = {"type": "object", "properties": props, "required": required}
            return {
                "type": "function",
                "name": name,
                "description": description,
                "parameters": schema,
            }

        path = {"type": "string", "description": "File path relative to the repository root"}
        return [
            tool(
                "read_file",
                f"Read up to {MAX_LINES} numbered lines of a file at the PR's head commit.",
                {"path": path, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
                ["path"],
            ),
            tool(
                "search_repo",
                f"Find a plain-text string in the repository (max {MAX_HITS} hits).",
                {"pattern": {"type": "string"}},
                ["pattern"],
            ),
            tool("view_diff_hunk", "Show this PR's diff for one file.", {"path": path}, ["path"]),
            tool(
                "list_related_tests",
                "List test files that look related to a source file.",
                {"path": path},
                ["path"],
            ),
        ]
