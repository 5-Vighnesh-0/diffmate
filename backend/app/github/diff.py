import asyncio
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path

import httpx

REVIEWED_SUFFIXES = (".py", ".ts", ".tsx")
MAX_FILES = 50
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024  # gzip can expand ~1000x: cap the real size too
MAX_MEMBERS = 20_000
MAX_LISTED_FILES = 300  # PR files fetched (3 pages) before filtering to Python/TypeScript
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class CheckoutError(Exception):
    pass


@dataclass
class PrFile:
    path: str
    status: str
    patch: str
    lines: set[int]  # new-side lines a review comment may target


def parse_patch(patch: str) -> set[int]:
    """New-side line numbers of added and context lines in a GitHub unified-diff patch."""
    lines: set[int] = set()
    new = 0
    for row in patch.splitlines():
        if m := HUNK.match(row):
            new = int(m.group(1))
        elif row.startswith(("+", " ")):
            lines.add(new)
            new += 1
        # "-" lines exist only on the old side; "\ No newline" is a marker
    return lines


async def get_pr_files(http: httpx.AsyncClient, token: str, repo: str, pr: int) -> list[PrFile]:
    listed = []
    for page in range(1, MAX_LISTED_FILES // 100 + 1):
        r = await http.get(
            f"/repos/{repo}/pulls/{pr}/files",
            params={"per_page": 100, "page": page},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        listed += r.json()
        if len(r.json()) < 100:
            break
    files = []
    for f in listed:
        if f["status"] == "removed" or not f["filename"].endswith(REVIEWED_SUFFIXES):
            continue
        patch = f.get("patch", "")
        files.append(PrFile(f["filename"], f["status"], patch, parse_patch(patch)))
    return files[:MAX_FILES]


def _extract(archive: Path, tree: Path, max_extracted_bytes: int) -> None:
    try:
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            if len(members) > MAX_MEMBERS:
                raise CheckoutError(f"archive has more than {MAX_MEMBERS} entries")
            if sum(m.size for m in members) > max_extracted_bytes:
                raise CheckoutError(f"archive expands past {max_extracted_bytes} bytes")
            # "data" filter: no absolute paths, no "..", no links leaving the folder, no devices.
            tar.extractall(tree, members=members, filter="data")
    except (tarfile.TarError, OSError) as e:
        raise CheckoutError(f"unsafe or broken archive: {type(e).__name__}") from e


async def checkout(
    http: httpx.AsyncClient,
    token: str,
    repo: str,
    sha: str,
    dest: Path,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
    max_extracted_bytes: int = MAX_EXTRACTED_BYTES,
) -> Path:
    """Download the repo at `sha` and extract it safely under `dest`. Returns the source root."""
    archive = dest / "src.tar.gz"
    size = 0
    async with http.stream(
        "GET",
        f"/repos/{repo}/tarball/{sha}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,  # GitHub redirects to codeload; httpx drops the auth header there
    ) as r:
        r.raise_for_status()
        with archive.open("wb") as out:
            async for chunk in r.aiter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise CheckoutError(f"repository archive is over {max_bytes} bytes")
                out.write(chunk)

    tree = dest / "tree"
    tree.mkdir()
    try:
        # Extraction is blocking work: keep it off the event loop so timeouts still fire.
        await asyncio.to_thread(_extract, archive, tree, max_extracted_bytes)
    finally:
        archive.unlink()

    roots = list(tree.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise CheckoutError("archive does not have a single top folder")
    return roots[0]


@dataclass
class PullInfo:
    title: str
    body: str
    github_repo_id: int


async def get_pull_request(http: httpx.AsyncClient, token: str, repo: str, pr: int) -> PullInfo:
    r = await http.get(f"/repos/{repo}/pulls/{pr}", headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    d = r.json()
    return PullInfo(d.get("title") or "", d.get("body") or "", int(d["base"]["repo"]["id"]))
