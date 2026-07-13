from __future__ import annotations

import os
from pathlib import Path

import pytest

from paths import ArsenalError, resolve_under_root


def test_valid_file_under_root(settings):
    result = resolve_under_root(settings, "PayloadsAllTheThings/XSS Injection/README.md")
    assert result.name == "README.md"


@pytest.mark.parametrize("value", ["/etc/passwd", "C:\\Windows\\win.ini", "../outside.txt", "a/../../b", "bad\x00.txt"])
def test_rejects_absolute_traversal_and_null(settings, value):
    with pytest.raises(ArsenalError):
        resolve_under_root(settings, value)


def test_rejects_unsupported_extension(settings):
    with pytest.raises(ArsenalError, match="supported"):
        resolve_under_root(settings, "SecLists/ignored.py")


def test_rejects_directory_as_file(settings):
    with pytest.raises(ArsenalError, match="not a file"):
        resolve_under_root(settings, "SecLists")


def test_prefix_confusion_is_not_contained(settings, tmp_path: Path):
    sibling = settings.arsenal_root.parent / f"{settings.arsenal_root.name}-evil"
    sibling.mkdir()
    (sibling / "file.txt").write_text("no", encoding="utf-8")
    with pytest.raises(ArsenalError):
        resolve_under_root(settings, "../arsenal-evil/file.txt")


@pytest.mark.skipif(os.name == "nt", reason="creating symlinks is not reliably permitted on Windows CI")
def test_symlink_escape(settings, tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (settings.arsenal_root / "escape.txt").symlink_to(outside)
    with pytest.raises(ArsenalError, match="outside"):
        resolve_under_root(settings, "escape.txt")
