"""Deterministic filename and bounded content search."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

from config import Settings
from paths import ArsenalError, resolve_collection, safe_relative, split_collection
from readers import is_probably_binary

MATCHES_PER_FILE = 10


def iter_supported_files(
    settings: Settings,
    collection: str | None = None,
    extensions: frozenset[str] | None = None,
) -> Iterator[Path]:
    base, _ = resolve_collection(settings, collection)
    allowed = settings.supported_extensions if extensions is None else extensions
    if not base.is_dir():
        return
    for path in sorted(base.rglob("*"), key=lambda item: item.as_posix().casefold()):
        try:
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            # Resolving each result also rejects file symlinks escaping the root.
            resolved = path.resolve()
            safe_relative(settings.arsenal_root, resolved)
            yield resolved
        except (OSError, ArsenalError):
            continue


def _filename_score(query: str, path: Path, arsenal_relative: str) -> tuple[int, int, str]:
    q = query.casefold()
    filename = path.name.casefold()
    stem = path.stem.casefold()
    rel = arsenal_relative.casefold()
    if q in (filename, stem):
        rank = 0
    elif filename.startswith(q):
        rank = 1
    elif q in filename:
        rank = 2
    else:
        rank = 3
    return rank, len(rel), rel


def search_files(
    settings: Settings,
    query: str,
    *,
    collection: str | None,
    extensions: frozenset[str],
    limit: int,
) -> dict[str, object]:
    deadline = time.monotonic() + settings.search_timeout_seconds
    matches: list[tuple[tuple[int, int, str], dict[str, object]]] = []
    timed_out = False
    for path in iter_supported_files(settings, collection, extensions):
        if time.monotonic() > deadline:
            timed_out = True
            break
        arsenal_relative = safe_relative(settings.arsenal_root, path)
        if query.casefold() not in arsenal_relative.casefold():
            continue
        collection_name, relative = split_collection(settings, path)
        item = {
            "collection": collection_name,
            "relative_path": relative,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        }
        matches.append((_filename_score(query, path, arsenal_relative), item))
    matches.sort(key=lambda pair: pair[0])
    returned = [item for _, item in matches[:limit]]
    return {
        "query": query,
        "count": len(matches),
        "returned": len(returned),
        "truncated": len(matches) > limit or timed_out,
        "timed_out": timed_out,
        "results": returned,
    }


def _direct_content_search(
    settings: Settings,
    query: str,
    *,
    collection: str | None,
    extensions: frozenset[str],
    case_sensitive: bool,
    limit: int,
    context_lines: int,
) -> dict[str, object]:
    needle = query if case_sensitive else query.casefold()
    results: list[dict[str, object]] = []
    seen: set[tuple[str, int, str]] = set()
    deadline = time.monotonic() + settings.search_timeout_seconds
    timed_out = False
    hit_limit = False

    for path in iter_supported_files(settings, collection, extensions):
        if time.monotonic() > deadline:
            timed_out = True
            break
        try:
            if path.stat().st_size > settings.max_file_bytes or is_probably_binary(path):
                continue
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read(settings.max_file_bytes + 1).splitlines()
        except OSError:
            continue
        per_file = 0
        collection_name, relative = split_collection(settings, path)
        for index, text in enumerate(lines):
            haystack = text if case_sensitive else text.casefold()
            if needle not in haystack:
                continue
            identity = (relative, index + 1, text)
            if identity in seen:
                continue
            seen.add(identity)
            before_start = max(0, index - context_lines)
            after_end = min(len(lines), index + context_lines + 1)
            occurrence_count = max(1, haystack.count(needle))
            filename_bonus = 0.15 if needle.casefold() in path.name.casefold() else 0
            score = min(1.0, 0.55 + 0.1 * occurrence_count + filename_bonus)
            results.append(
                {
                    "collection": collection_name,
                    "relative_path": relative,
                    "line": index + 1,
                    "matched_text": text,
                    "context_before": lines[before_start:index],
                    "context_after": lines[index + 1 : after_end],
                    "score": round(score, 3),
                }
            )
            per_file += 1
            if len(results) >= limit or per_file >= MATCHES_PER_FILE:
                hit_limit = len(results) >= limit
                break
        if hit_limit:
            break

    results.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["collection"]).casefold(),
            str(item["relative_path"]).casefold(),
            int(item["line"]),
        )
    )
    return {
        "query": query,
        "count": len(results),
        "returned": len(results),
        "truncated": hit_limit or timed_out,
        "timed_out": timed_out,
        "search_backend": "direct",
        "results": results[:limit],
    }


def search_content(
    settings: Settings,
    query: str,
    *,
    collection: str | None,
    extensions: frozenset[str],
    case_sensitive: bool,
    limit: int,
    context_lines: int,
    index: object | None = None,
) -> dict[str, object]:
    if index is not None and settings.index_enabled and not case_sensitive:
        try:
            indexed = index.search_content(
                query,
                collection=collection,
                extensions=extensions,
                limit=limit,
                context_lines=context_lines,
            )
            if indexed is not None:
                return indexed
        except Exception:
            # Index failures are deliberately non-fatal; callers log diagnostics.
            pass
    return _direct_content_search(
        settings,
        query,
        collection=collection,
        extensions=extensions,
        case_sensitive=case_sensitive,
        limit=limit,
        context_lines=context_lines,
    )
