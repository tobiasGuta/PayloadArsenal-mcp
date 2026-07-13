from __future__ import annotations

from pathlib import Path

import pytest

from config import Settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def arsenal(tmp_path: Path) -> Path:
    root = tmp_path / "arsenal"
    patt = root / "PayloadsAllTheThings" / "XSS Injection"
    sec = root / "SecLists" / "Discovery" / "Web-Content"
    patt.mkdir(parents=True)
    sec.mkdir(parents=True)
    (patt / "README.md").write_text(
        "# XSS Injection\n\n## Attribute context\nUse authorized manual testing.\n"
        "```html\n' onmouseover=example(1) x='\n```\nUnicode: café 🚀\n",
        encoding="utf-8",
    )
    (patt / "notes.txt").write_text("first\nUNION SELECT example\nthird\nfourth\n", encoding="utf-8")
    (sec / "graphql.txt").write_text("graphql\napi/graphql\nquery\n", encoding="utf-8")
    (sec / "BINARY.txt").write_bytes(b"text\x00binary")
    (root / "SecLists" / "ignored.py").write_text("UNION SELECT", encoding="utf-8")
    return root


@pytest.fixture
def settings(arsenal: Path, tmp_path: Path) -> Settings:
    return Settings(
        arsenal_root=arsenal.resolve(),
        max_response_bytes=16_384,
        max_file_bytes=100_000,
        default_read_lines=2,
        max_read_lines=10,
        max_search_results=20,
        search_timeout_seconds=5,
        index_enabled=True,
        index_path=tmp_path / "index.sqlite3",
        max_query_length=100,
    )
