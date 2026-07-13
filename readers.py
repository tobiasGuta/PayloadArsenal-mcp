"""Bounded, binary-aware text reading."""

from __future__ import annotations

from pathlib import Path

from config import Settings
from paths import ArsenalError, resolve_under_root, split_collection

BINARY_SAMPLE_BYTES = 8_192


def is_probably_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            sample = handle.read(BINARY_SAMPLE_BYTES)
    except OSError as exc:
        raise ArsenalError("file could not be inspected") from exc
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    suspicious = sum(byte < 9 or 13 < byte < 32 for byte in sample)
    return suspicious / len(sample) > 0.10


def read_line_range(
    settings: Settings,
    relative_path: str,
    *,
    start_line: int = 1,
    end_line: int | None = None,
    max_lines: int | None = None,
) -> dict[str, object]:
    path = resolve_under_root(settings, relative_path)
    if is_probably_binary(path):
        raise ArsenalError("binary files are not readable")

    requested_lines = max_lines or settings.default_read_lines
    if end_line is not None:
        requested_lines = end_line - start_line + 1
    final_line = start_line + requested_lines - 1
    file_size = path.stat().st_size
    content: list[dict[str, object]] = []
    content_bytes = 0
    has_more = False
    last_seen = 0
    bytes_scanned = 0
    maximum_line_bytes = max(1, min(settings.max_file_bytes, settings.max_response_bytes // 2))

    try:
        with path.open("rb") as handle:
            line_number = 0
            while True:
                remaining_scan = settings.max_file_bytes - bytes_scanned
                if remaining_scan <= 0:
                    has_more = True
                    break
                raw_line = handle.readline(min(maximum_line_bytes + 1, remaining_scan))
                if not raw_line:
                    break
                line_number += 1
                last_seen = line_number
                bytes_scanned += len(raw_line)
                complete_line = raw_line.endswith(b"\n") or handle.tell() >= file_size
                if line_number < start_line:
                    if not complete_line:
                        raise ArsenalError("requested range requires scanning beyond the safe byte limit")
                    continue
                if line_number > final_line:
                    has_more = True
                    break
                text = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                # Reserve response space for JSON keys and metadata.
                encoded_size = len(text.encode("utf-8")) + 64
                if content_bytes + encoded_size > max(1, settings.max_response_bytes // 2):
                    has_more = True
                    break
                content.append({"line": line_number, "text": text})
                content_bytes += encoded_size
                if not complete_line:
                    has_more = True
                    break
    except OSError as exc:
        raise ArsenalError("file could not be read") from exc

    collection, collection_relative = split_collection(settings, path)
    returned_end = int(content[-1]["line"]) if content else min(last_seen, final_line)
    return {
        "collection": collection,
        "relative_path": collection_relative,
        "start_line": start_line,
        "end_line": returned_end,
        "returned_lines": len(content),
        "file_size_bytes": file_size,
        "bytes_scanned": bytes_scanned,
        "truncated": has_more,
        "content": content,
    }


def approximate_line_count(path: Path, sample_bytes: int = 131_072) -> int:
    size = path.stat().st_size
    if size == 0:
        return 0
    with path.open("rb") as handle:
        sample = handle.read(sample_bytes)
    if not sample:
        return 0
    newlines = sample.count(b"\n")
    if len(sample) == size:
        return newlines + (0 if sample.endswith(b"\n") else 1)
    return max(1, round(newlines * size / len(sample)))
