import io
import tarfile

import httpx
import pytest

from app.github.diff import CheckoutError, checkout, get_pr_files, parse_patch

PATCH = """@@ -1,4 +1,5 @@
 import os
-x = 1
+x = 2
+y = 3
 print(x)
\\ No newline at end of file
@@ -20,2 +21,2 @@ def f():
-    return a
+    return b
     # end"""


def test_parse_patch_returns_new_side_lines_for_added_and_context():
    # hunk 1: 1 context, 2-3 added, 4 context; hunk 2 starts at 21: 21 added, 22 context
    assert parse_patch(PATCH) == {1, 2, 3, 4, 21, 22}


def test_parse_patch_of_empty_patch_is_empty():
    assert parse_patch("") == set()


def http_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.x")


async def test_get_pr_files_keeps_python_and_typescript_and_skips_removed():
    files = [
        {"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b"},
        {"filename": "web/b.tsx", "status": "added", "patch": "@@ -0,0 +1 @@\n+x"},
        {"filename": "README.md", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b"},
        {"filename": "old.py", "status": "removed", "patch": "@@ -1 +0,0 @@\n-a"},
        {"filename": "big.py", "status": "modified"},  # GitHub omits patch for huge diffs
    ]

    async with http_for(lambda r: httpx.Response(200, json=files)) as http:
        result = await get_pr_files(http, "t", "o/r", 7)

    assert [(f.path, f.lines) for f in result] == [
        ("a.py", {1}),
        ("web/b.tsx", {1}),
        ("big.py", set()),
    ]


def tarball(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


async def test_checkout_extracts_the_single_top_folder(tmp_path):
    body = tarball({"o-r-abc/app.py": b"print(1)\n"})

    async with http_for(lambda r: httpx.Response(200, content=body)) as http:
        root = await checkout(http, "t", "o/r", "abc", tmp_path)

    assert (root / "app.py").read_text() == "print(1)\n"


async def test_checkout_refuses_members_escaping_the_folder(tmp_path):
    body = tarball({"o-r-abc/ok.py": b"", "../evil.py": b"x"})

    async with http_for(lambda r: httpx.Response(200, content=body)) as http:
        with pytest.raises(CheckoutError):
            await checkout(http, "t", "o/r", "abc", tmp_path)

    assert not (tmp_path.parent / "evil.py").exists()


async def test_checkout_refuses_downloads_over_the_size_limit(tmp_path):
    body = tarball({"o-r-abc/big.bin": b"0" * 2048})

    async with http_for(lambda r: httpx.Response(200, content=body)) as http:
        with pytest.raises(CheckoutError):
            await checkout(http, "t", "o/r", "abc", tmp_path, max_bytes=100)


async def test_checkout_refuses_archives_that_expand_past_the_limit(tmp_path):
    body = tarball({"o-r-abc/zeros.bin": b"0" * 5000})  # compresses to a few bytes

    async with http_for(lambda r: httpx.Response(200, content=body)) as http:
        with pytest.raises(CheckoutError):
            await checkout(http, "t", "o/r", "abc", tmp_path, max_extracted_bytes=1000)

    assert not list((tmp_path / "tree").rglob("zeros.bin"))


async def test_get_pr_files_follows_pagination():
    page = [{"filename": f"f{i}.md", "status": "modified", "patch": ""} for i in range(100)]
    last = [{"filename": "late.py", "status": "modified", "patch": "@@ -1 +1 @@\n+x"}]

    def handler(r):
        return httpx.Response(200, json=page if r.url.params["page"] == "1" else last)

    async with http_for(handler) as http:
        files = await get_pr_files(http, "t", "o/r", 7)

    assert [f.path for f in files] == ["late.py"]
