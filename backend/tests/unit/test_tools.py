import pytest

from app.agent.tools import Tools
from app.github.diff import PrFile


@pytest.fixture
def tools(tmp_path):
    root = tmp_path / "repo"
    (root / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "app" / "calc.py").write_text("".join(f"line {i}\n" for i in range(1, 301)))
    (root / "app" / "util.ts").write_text("export const TOKEN_NAME = 'x';\n")
    (root / "tests" / "test_calc.py").write_text("from app.calc import add\n")
    (root / "app" / "calc.test.ts").write_text("test('x', () => {});\n")
    (tmp_path / "secret.txt").write_text("outside")
    (root / "link.txt").symlink_to(tmp_path / "secret.txt")
    files = [PrFile("app/calc.py", "modified", "@@ -1 +1 @@\n-a\n+b", {1})]
    return Tools(root, files)


def test_read_file_returns_numbered_lines_in_range(tools):
    assert tools.read_file("app/calc.py", 2, 3) == "2: line 2\n3: line 3"


def test_read_file_returns_at_most_200_lines(tools):
    assert len(tools.read_file("app/calc.py", 1, 300).splitlines()) == 200


@pytest.mark.parametrize(
    "path", ["../secret.txt", "/etc/passwd", "link.txt", "app/../../secret.txt"]
)
def test_paths_outside_the_checkout_are_refused(tools, path):
    out = tools.read_file(path)

    assert out.startswith("error:")
    assert "outside" not in out.replace("outside the repository", "")


def test_missing_file_is_an_error_message_not_an_exception(tools):
    assert tools.read_file("nope.py").startswith("error:")


def test_search_repo_finds_plain_text_with_locations(tools):
    assert tools.search_repo("TOKEN_NAME") == "app/util.ts:1: export const TOKEN_NAME = 'x';"


def test_search_repo_caps_hits(tools):
    assert len(tools.search_repo("line").splitlines()) == 30


def test_search_repo_rejects_too_short_patterns(tools):
    assert tools.search_repo("a").startswith("error:")


def test_view_diff_hunk_only_for_files_in_the_pr(tools):
    assert tools.view_diff_hunk("app/calc.py") == "@@ -1 +1 @@\n-a\n+b"
    assert tools.view_diff_hunk("app/util.ts").startswith("error:")


def test_list_related_tests_matches_python_and_ts_conventions(tools):
    assert tools.list_related_tests("app/calc.py") == "app/calc.test.ts\ntests/test_calc.py"


def test_call_dispatches_and_refuses_unknown_tools_and_bad_args(tools):
    assert tools.call("read_file", {"path": "app/calc.py", "start_line": 1, "end_line": 1}) == (
        "1: line 1"
    )
    assert tools.call("run_shell", {"cmd": "ls"}).startswith("error: unknown tool")
    assert tools.call("read_file", {"nope": 1}).startswith("error: invalid arguments")


def test_declarations_list_exactly_the_four_read_only_tools(tools):
    names = [d["name"] for d in tools.declarations()]

    assert names == ["read_file", "search_repo", "view_diff_hunk", "list_related_tests"]


def test_read_file_truncates_long_lines_and_caps_output(tools, tmp_path):
    (tools.root / "min.js").write_text("x" * 5000 + "\n" + ("y" * 400 + "\n") * 199)

    out = tools.read_file("min.js")

    assert len(out.splitlines()[0]) < 600
    assert len(out) <= 20_000


def test_read_file_refuses_huge_files(tools):
    (tools.root / "big.py").write_bytes(b"a" * 1_000_001)

    assert tools.read_file("big.py").startswith("error:")


def test_symlink_loops_are_errors_not_crashes(tools):
    (tools.root / "l1.py").symlink_to(tools.root / "l2.py")
    (tools.root / "l2.py").symlink_to(tools.root / "l1.py")

    assert tools.call("read_file", {"path": "l1.py"}).startswith("error:")
