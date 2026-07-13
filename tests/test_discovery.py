from __future__ import annotations

from categories import discover_categories
from references import find_payload_references
from wordlists import find_wordlists


def test_categories_come_from_directories_and_headings(settings):
    result = discover_categories(settings, collection="PayloadsAllTheThings", depth=2, limit=20)
    assert any(
        item["name"] == "XSS Injection" and item["category_source"] == "directory" for item in result["categories"]
    )
    assert any(
        item["name"] == "Attribute context" and item["category_source"] == "markdown-heading"
        for item in result["categories"]
    )


def test_categories_depth_and_limit(settings):
    result = discover_categories(settings, collection=None, depth=1, limit=1)
    assert result["returned"] == 1
    assert result["truncated"] is True


def test_payloads_are_source_derived_with_provenance_and_limits(settings):
    result = find_payload_references(
        settings,
        vulnerability_class="xss",
        context="attribute",
        constraints=[],
        collection="PayloadsAllTheThings",
        limit=1,
    )
    assert result["returned"] == 1
    item = result["results"][0]
    assert item["source_derived"] is True
    assert item["payload"] == "' onmouseover=example(1) x='"
    assert item["start_line"] <= item["end_line"]
    assert item["explanation"]


def test_no_payload_is_invented(settings):
    result = find_payload_references(
        settings, vulnerability_class="nonexistent", context=None, constraints=[], collection=None, limit=5
    )
    assert result["results"] == []


def test_wordlist_metadata_relevance_size_and_no_contents(settings):
    result = find_wordlists(
        settings,
        purpose="api endpoint discovery",
        technology="graphql",
        collection="SecLists",
        maximum_files=5,
        maximum_size_bytes=1000,
    )
    assert result["results"][0]["relative_path"].endswith("graphql.txt")
    assert result["results"][0]["line_count"] == 3
    assert "content" not in result["results"][0]
    assert "advisory" in result["disclaimer"].lower()
