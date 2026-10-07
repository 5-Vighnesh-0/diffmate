import shutil

import pytest

from app.checks import linters
from app.checks.linters import LintHint, run_linters


async def test_ruff_reports_bug_rules_with_relative_paths(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "bad.py").write_text("import os\n\n\ndef f():\n    return missing_name\n")
    # The PR's own config must be ignored (it tries to switch every rule off).
    (tmp_path / "pyproject.toml").write_text("[tool.ruff.lint]\nignore = ['ALL']\n")

    hints = await run_linters(tmp_path, ["pkg/bad.py"])

    assert LintHint("pkg/bad.py", 5, "F821", "Undefined name `missing_name`") in hints
    assert any(h.rule == "F401" and h.line == 1 for h in hints)


async def test_paths_outside_the_checkout_are_not_linted(tmp_path):
    (tmp_path.parent / "outside.py").write_text("import os\n")

    assert await run_linters(tmp_path, ["../outside.py"]) == []


async def test_a_broken_linter_gives_no_hints_instead_of_failing(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("import os\n")
    monkeypatch.setattr(linters, "RUFF", ["/nonexistent/ruff"])

    assert await run_linters(tmp_path, ["a.py"]) == []


@pytest.mark.skipif(
    not shutil.which("node") or not (linters.ESLINT_DIR / "node_modules").exists(),
    reason="Node or the bundled ESLint is not installed",
)
async def test_eslint_reports_typescript_problems(tmp_path):
    (tmp_path / "x.ts").write_text("const unused = 1;\nexport const y: any = 2;\n")
    (tmp_path / "eslint.config.mjs").write_text("throw new Error('PR config must not run');\n")

    hints = await run_linters(tmp_path, ["x.ts"])

    rules = {(h.line, h.rule) for h in hints}
    assert (1, "@typescript-eslint/no-unused-vars") in rules
    assert (2, "@typescript-eslint/no-explicit-any") in rules


def test_hint_text_is_one_line():
    assert str(LintHint("a.py", 3, "F821", "Undefined name")) == "a.py:3 F821 Undefined name"


async def test_files_named_like_options_are_linted_as_files_not_options(tmp_path):
    # Without "--", ruff would read this name as its --fix flag and rewrite the PR's files.
    evil = tmp_path / "--fix.py"
    evil.write_text("import os\n")

    hints = await run_linters(tmp_path, ["--fix.py"])

    assert evil.read_text() == "import os\n"
    assert any(h.file == "--fix.py" and h.rule == "F401" for h in hints)


async def test_a_symlink_loop_gives_no_hints_instead_of_crashing(tmp_path):
    (tmp_path / "a.py").symlink_to(tmp_path / "b.py")
    (tmp_path / "b.py").symlink_to(tmp_path / "a.py")

    assert await run_linters(tmp_path, ["a.py"]) == []
