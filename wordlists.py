"""Wordlist discovery and advisory relevance metadata."""

from __future__ import annotations

import re

from config import Settings
from paths import split_collection
from readers import approximate_line_count, is_probably_binary
from search import iter_supported_files

WORDLIST_EXTENSIONS = frozenset({".txt", ".lst", ".list", ".csv"})


def _terms(value: str | None) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", (value or "").casefold()) if len(term) > 1}


def find_wordlists(
    settings: Settings,
    *,
    purpose: str,
    technology: str | None,
    collection: str | None,
    maximum_files: int,
    maximum_size_bytes: int | None,
) -> dict[str, object]:
    purpose_terms = _terms(purpose)
    technology_terms = _terms(technology)
    ranked: list[tuple[float, str, dict[str, object]]] = []
    for path in iter_supported_files(settings, collection, WORDLIST_EXTENSIONS):
        try:
            size = path.stat().st_size
            if maximum_size_bytes is not None and size > maximum_size_bytes:
                continue
            if size > settings.max_file_bytes or is_probably_binary(path):
                continue
            collection_name, relative = split_collection(settings, path)
            path_terms = _terms(relative)
            purpose_hits = len(purpose_terms & path_terms)
            technology_hits = len(technology_terms & path_terms)
            if purpose_hits == 0 and technology_hits == 0:
                continue
            denominator = max(1, len(purpose_terms) + len(technology_terms))
            score = min(1.0, 0.25 + (purpose_hits + 1.5 * technology_hits) / denominator * 0.6)
            descriptor = " / ".join(part.replace("-", " ").replace("_", " ") for part in path.parent.parts[-2:])
            suggested_use = f"Advisory candidate for {purpose}"
            if technology:
                suggested_use += f" with {technology}"
            if descriptor:
                suggested_use += f" ({descriptor})"
            ranked.append(
                (
                    score,
                    relative.casefold(),
                    {
                        "collection": collection_name,
                        "relative_path": relative,
                        "size_bytes": size,
                        "line_count": approximate_line_count(path),
                        "line_count_approximate": size > 131_072,
                        "suggested_use": suggested_use,
                        "relevance_score": round(score, 3),
                    },
                )
            )
        except OSError:
            continue
    ranked.sort(key=lambda item: (-item[0], item[1]))
    results = [item for _, _, item in ranked[:maximum_files]]
    return {
        "purpose": purpose,
        "technology": technology,
        "count": len(ranked),
        "returned": len(results),
        "truncated": len(ranked) > maximum_files,
        "results": results,
        "disclaimer": "Relevance is advisory; no wordlist is claimed to be optimal or complete.",
    }
