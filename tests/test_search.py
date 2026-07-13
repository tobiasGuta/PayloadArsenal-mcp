from __future__ import annotations

from indexing import ArsenalIndex
from schemas import SearchFilesRequest, parse_request, validate_extensions
from search import search_content, search_files


def test_file_search_case_filter_ranking_and_limit(settings):
    sibling = settings.arsenal_root / "SecLists" / "Discovery" / "graphql-notes.txt"
    sibling.write_text("notes", encoding="utf-8")
    result = search_files(settings, "GRAPHQL", collection="SecLists", extensions=frozenset({".txt"}), limit=1)
    assert result["returned"] == 1
    assert result["results"][0]["filename"] == "graphql.txt"
    assert result["results"][0]["extension"] == ".txt"


def test_file_search_empty_and_deterministic(settings):
    first = search_files(settings, "missing", collection=None, extensions=settings.supported_extensions, limit=20)
    second = search_files(settings, "missing", collection=None, extensions=settings.supported_extensions, limit=20)
    assert first == second
    assert first["results"] == []


def test_empty_extension_filter_matches_nothing(settings):
    result = search_files(settings, "graphql", collection=None, extensions=frozenset(), limit=20)
    assert result["results"] == []


def test_query_length_and_extension_validation(settings):
    try:
        parse_request(SearchFilesRequest, {"query": "x" * 101}, settings)
    except ValueError as exc:
        assert "maximum" in str(exc)
    else:
        raise AssertionError("long query accepted")
    try:
        validate_extensions([".exe"], settings)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported extension accepted")


def test_content_lines_context_case_and_duplicate_suppression(settings):
    result = search_content(
        settings,
        "union select",
        collection="PayloadsAllTheThings",
        extensions=frozenset({".txt"}),
        case_sensitive=False,
        limit=10,
        context_lines=1,
    )
    assert result["results"][0]["line"] == 2
    assert result["results"][0]["context_before"] == ["first"]
    assert len({(item["relative_path"], item["line"], item["matched_text"]) for item in result["results"]}) == len(
        result["results"]
    )
    sensitive = search_content(
        settings,
        "union select",
        collection=None,
        extensions=frozenset({".txt"}),
        case_sensitive=True,
        limit=10,
        context_lines=0,
    )
    assert sensitive["results"] == []


def test_content_cap_and_unsupported_skipped(settings):
    result = search_content(
        settings,
        "UNION SELECT",
        collection=None,
        extensions=settings.supported_extensions,
        case_sensitive=True,
        limit=1,
        context_lines=0,
    )
    assert result["returned"] == 1
    assert all(not item["relative_path"].endswith(".py") for item in result["results"])


def test_index_creation_search_and_corrupt_fallback(settings):
    index = ArsenalIndex(settings)
    built = index.build()
    assert built["indexed"] >= 3
    indexed = search_content(
        settings,
        "graphql",
        collection="SecLists",
        extensions=frozenset({".txt"}),
        case_sensitive=False,
        limit=5,
        context_lines=0,
        index=index,
    )
    assert indexed["search_backend"] == "sqlite-fts5"
    settings.index_path.write_bytes(b"corrupt")
    fallback = search_content(
        settings,
        "graphql",
        collection="SecLists",
        extensions=frozenset({".txt"}),
        case_sensitive=False,
        limit=5,
        context_lines=0,
        index=index,
    )
    assert fallback["search_backend"] == "direct"


def test_disabled_index_and_oversized_file_are_skipped(settings):
    oversized = settings.arsenal_root / "SecLists" / "oversized.txt"
    oversized.write_text("needle" * 20_000, encoding="utf-8")
    built = ArsenalIndex(settings).build()
    assert built["skipped"] >= 2  # binary fixture plus oversized file
    disabled = settings.__class__(**{**settings.__dict__, "index_enabled": False})
    result = search_content(
        disabled,
        "graphql",
        collection="SecLists",
        extensions=frozenset({".txt"}),
        case_sensitive=False,
        limit=5,
        context_lines=0,
        index=ArsenalIndex(disabled),
    )
    assert result["search_backend"] == "direct"
