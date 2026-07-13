"""Dynamic category discovery from directories and Markdown headings."""

from __future__ import annotations

import re
import time

from config import Settings
from paths import resolve_collection, safe_relative
from readers import is_probably_binary

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def discover_categories(settings: Settings, *, collection: str | None, depth: int, limit: int) -> dict[str, object]:
    base, selected = resolve_collection(settings, collection)
    deadline = time.monotonic() + settings.search_timeout_seconds
    entries: list[dict[str, object]] = []
    timed_out = False

    directories = sorted(
        (path for path in base.rglob("*") if path.is_dir()),
        key=lambda path: path.as_posix().casefold(),
    )
    for directory in directories:
        relative_parts = directory.relative_to(base).parts
        if not relative_parts or len(relative_parts) > depth:
            continue
        if time.monotonic() > deadline:
            timed_out = True
            break
        file_count = sum(
            1
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in settings.supported_extensions
        )
        entries.append(
            {
                "name": directory.name.replace("_", " ").strip(),
                "relative_path": safe_relative(settings.arsenal_root, directory),
                "file_count": file_count,
                "category_source": "directory",
            }
        )
        if len(entries) >= limit:
            break

    if len(entries) < limit and not timed_out:
        markdown = sorted(base.rglob("*.md"), key=lambda path: path.as_posix().casefold())
        for document in markdown:
            if time.monotonic() > deadline:
                timed_out = True
                break
            try:
                if document.stat().st_size > settings.max_file_bytes or is_probably_binary(document):
                    continue
                with document.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, 1):
                        match = HEADING_RE.match(line.rstrip())
                        if not match or len(match.group(1)) > depth:
                            continue
                        entries.append(
                            {
                                "name": match.group(2).strip().rstrip("#").strip(),
                                "relative_path": safe_relative(settings.arsenal_root, document),
                                "file_count": 1,
                                "category_source": "markdown-heading",
                                "line": line_number,
                            }
                        )
                        if len(entries) >= limit:
                            break
            except OSError:
                continue
            if len(entries) >= limit:
                break

    return {
        "collection": selected,
        "count": len(entries),
        "returned": len(entries),
        "truncated": len(entries) >= limit or timed_out,
        "timed_out": timed_out,
        "categories": entries[:limit],
    }
