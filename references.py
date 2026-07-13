"""Source-derived payload and methodology passage retrieval."""

from __future__ import annotations

import re
import time

from config import Settings
from paths import split_collection
from readers import is_probably_binary
from search import iter_supported_files

INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\r\n]{1,500})`(?!`)")
TERM_RE = re.compile(r"[a-z0-9_+-]+")


def _terms(*values: str) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(term for term in TERM_RE.findall(value.casefold()) if len(term) > 1)
    return list(dict.fromkeys(result))


def _source_payload(line: str, in_fence: bool) -> str | None:
    inline = INLINE_CODE_RE.search(line)
    if inline:
        candidate = inline.group(1).strip()
        return candidate or None
    stripped = line.strip()
    if in_fence and stripped and not stripped.startswith(("#", "//")):
        return stripped[:500]
    if line.startswith(("    ", "\t")) and stripped:
        return stripped[:500]
    return None


def find_payload_references(
    settings: Settings,
    *,
    vulnerability_class: str,
    context: str | None,
    constraints: list[str],
    collection: str | None,
    limit: int,
) -> dict[str, object]:
    terms = _terms(vulnerability_class, context or "", *constraints)
    required_terms = set(_terms(vulnerability_class))
    candidates: list[tuple[float, str, int, dict[str, object]]] = []
    deadline = time.monotonic() + settings.search_timeout_seconds
    timed_out = False

    for path in iter_supported_files(settings, collection):
        if time.monotonic() > deadline:
            timed_out = True
            break
        try:
            if path.stat().st_size > settings.max_file_bytes or is_probably_binary(path):
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        collection_name, relative = split_collection(settings, path)
        path_text = relative.casefold()
        path_hits = sum(term in path_text for term in terms)
        if required_terms and not any(term in path_text for term in required_terms):
            # Content can still establish relevance below.
            path_hits = 0
        in_fence = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            line_folded = line.casefold()
            text_hits = sum(term in line_folded for term in terms)
            neighborhood = " ".join(lines[max(0, index - 2) : index + 3]).casefold()
            neighborhood_required = any(term in neighborhood or term in path_text for term in required_terms)
            if not neighborhood_required or path_hits + text_hits == 0:
                continue
            payload = _source_payload(line, in_fence)
            constraint_hits = sum(term in neighborhood for term in _terms(*constraints))
            context_hits = sum(term in neighborhood or term in path_text for term in _terms(context or ""))
            score = min(
                1.0,
                0.35
                + path_hits * 0.08
                + text_hits * 0.12
                + context_hits * 0.08
                + constraint_hits * 0.05
                + (0.25 if payload else 0),
            )
            start = max(0, index - 2)
            end = min(len(lines), index + 3)
            explanation_lines = [
                text.strip()
                for text in lines[start:end]
                if text.strip() and not text.strip().startswith(("```", "~~~"))
            ]
            candidates.append(
                (
                    score,
                    relative.casefold(),
                    index + 1,
                    {
                        "result_type": "payload" if payload else "methodology",
                        "payload": payload,
                        "source_derived": True,
                        "collection": collection_name,
                        "relative_path": relative,
                        "start_line": start + 1,
                        "end_line": end,
                        "explanation": " ".join(explanation_lines)[:1_500],
                        "relevance_score": round(score, 3),
                    },
                )
            )

    # Exact duplicate source passages or payloads are not useful.
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    results: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for _, _, _, item in candidates:
        identity = (item["collection"], item["relative_path"], item["start_line"], item["payload"])
        if identity in seen:
            continue
        seen.add(identity)
        results.append(item)
        if len(results) >= limit:
            break
    return {
        "query": {
            "vulnerability_class": vulnerability_class,
            "context": context,
            "constraints": constraints,
        },
        "count": len(candidates),
        "returned": len(results),
        "truncated": len(candidates) > limit or timed_out,
        "timed_out": timed_out,
        "results": results,
        "warning": (
            "Returned content is source-derived reference material for authorized manual testing. "
            "No payload was generated, executed, or tested."
        ),
    }
