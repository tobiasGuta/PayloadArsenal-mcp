#!/usr/bin/env python3
"""Fetch pinned GitHub commit archives during the Docker build only."""

from __future__ import annotations

import json
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REVISION_RE = re.compile(r"[0-9a-f]{40}")
GITHUB_REPOSITORY_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\.git")


def fetch(metadata_path: Path, destination: Path) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["collections"]
    destination.mkdir(parents=True, exist_ok=True)
    for name, source in sorted(metadata.items()):
        repository = source["repository"]
        revision = source["revision"]
        repository_match = GITHUB_REPOSITORY_RE.fullmatch(repository)
        if not repository_match or not REVISION_RE.fullmatch(revision):
            raise ValueError(f"invalid pinned collection metadata for {name}")
        owner, repository_name = repository_match.groups()
        url = f"https://github.com/{owner}/{repository_name}/archive/{revision}.tar.gz"
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            archive_path = temporary_path / "collection.tar.gz"
            request = urllib.request.Request(url, headers={"User-Agent": "payload-arsenal-mcp-build/1.0.0"})
            with urllib.request.urlopen(request, timeout=300) as response, archive_path.open("wb") as archive:
                shutil.copyfileobj(response, archive)
            extract_path = temporary_path / "extracted"
            with tarfile.open(archive_path, "r:gz") as bundle:
                bundle.extractall(extract_path, filter="data")
            roots = list(extract_path.iterdir())
            if len(roots) != 1 or not roots[0].is_dir():
                raise ValueError(f"unexpected archive layout for {name}")
            shutil.copytree(roots[0], destination / name, symlinks=False)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: fetch_collections.py METADATA DESTINATION")
    fetch(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
