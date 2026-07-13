from __future__ import annotations

import json
import sqlite3
from contextlib import closing

import pytest

from indexing import ArsenalIndex
from paths import ArsenalError
from schemas import ReadFileRequest, SearchContentRequest, parse_request
from service import ArsenalService


def test_conflicting_ranges_and_maximum_lines_are_rejected(settings):
    with pytest.raises(ArsenalError, match="cannot both"):
        parse_request(
            ReadFileRequest,
            {"relative_path": "SecLists/a.txt", "start_line": 1, "end_line": 2, "max_lines": 2},
            settings,
        )
    with pytest.raises(ArsenalError, match="maximum"):
        parse_request(
            ReadFileRequest,
            {"relative_path": "SecLists/a.txt", "start_line": 1, "end_line": 20},
            settings,
        )


def test_strict_types_context_bounds_and_unexpected_fields(settings):
    with pytest.raises(ArsenalError):
        parse_request(SearchContentRequest, {"query": "x", "limit": "5"}, settings)
    with pytest.raises(ArsenalError, match="context_lines"):
        parse_request(SearchContentRequest, {"query": "x", "context_lines": 6}, settings)
    with pytest.raises(ArsenalError, match="Extra inputs"):
        parse_request(SearchContentRequest, {"query": "x", "surprise": True}, settings)


def test_service_adds_revision_provenance_without_host_paths(settings):
    result = ArsenalService(settings).read_file(
        {"relative_path": "PayloadsAllTheThings/XSS Injection/README.md", "max_lines": 1}
    )
    assert result["source"]["collection_revision"] != ""
    assert str(settings.arsenal_root) not in json.dumps(result)


def test_index_records_collection_revision(settings):
    index = ArsenalIndex(settings)
    index.build()
    with closing(sqlite3.connect(settings.index_path)) as connection:
        revisions = {row[0] for row in connection.execute("SELECT DISTINCT revision FROM documents")}
    assert "5443cbde384134094f25b1b440695757a2803d55" in revisions


def test_index_writer_rejects_path_inside_arsenal(settings):
    unsafe = settings.__class__(**{**settings.__dict__, "index_path": settings.arsenal_root / "index.sqlite3"})
    with pytest.raises(ArsenalError, match="inside"):
        ArsenalIndex(unsafe).build()
