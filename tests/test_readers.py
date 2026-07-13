from __future__ import annotations

import json

import pytest

from paths import ArsenalError
from readers import read_line_range


def test_line_range_and_numbering(settings):
    result = read_line_range(settings, "PayloadsAllTheThings/XSS Injection/notes.txt", start_line=2, end_line=3)
    assert result["content"] == [{"line": 2, "text": "UNION SELECT example"}, {"line": 3, "text": "third"}]
    assert result["relative_path"] == "XSS Injection/notes.txt"
    assert str(settings.arsenal_root) not in json.dumps(result)


def test_default_limit_sets_truncation(settings):
    result = read_line_range(settings, "PayloadsAllTheThings/XSS Injection/notes.txt")
    assert result["returned_lines"] == 2
    assert result["truncated"] is True


def test_binary_rejected(settings):
    with pytest.raises(ArsenalError, match="binary"):
        read_line_range(settings, "SecLists/Discovery/Web-Content/BINARY.txt")


def test_missing_file_is_controlled(settings):
    with pytest.raises(ArsenalError, match="does not exist"):
        read_line_range(settings, "SecLists/missing.txt")


def test_invalid_utf8_is_replaced(settings):
    path = settings.arsenal_root / "SecLists" / "bad.txt"
    path.write_bytes(b"good\ninvalid:\xff\n")
    result = read_line_range(settings, "SecLists/bad.txt", max_lines=2)
    assert "�" in result["content"][1]["text"]


def test_large_file_is_streamed_and_bounded(settings):
    path = settings.arsenal_root / "SecLists" / "large.txt"
    path.write_text("x" * 200_000 + "\nsecond\n", encoding="utf-8")
    result = read_line_range(settings, "SecLists/large.txt", max_lines=2)
    assert result["file_size_bytes"] > settings.max_file_bytes
    assert result["bytes_scanned"] <= settings.max_file_bytes
    assert result["truncated"] is True
