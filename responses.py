"""Shared UTF-8 response bounding and MCP result construction."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult, TextContent


def serialized_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _utf8_prefix(value: str, maximum: int) -> str:
    encoded = value.encode("utf-8")[:maximum]
    while encoded:
        try:
            return encoded.decode("utf-8")
        except UnicodeDecodeError:
            encoded = encoded[:-1]
    return ""


def bound_response(data: dict[str, Any], maximum_bytes: int) -> dict[str, Any]:
    original = serialized_size(data)
    # Leave room for the MCP envelope and concise readable content block.
    target = max(1_024, maximum_bytes - 2_048)
    if original <= target:
        return data
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    envelope: dict[str, Any] = {
        "truncated": True,
        "original_response_bytes": original,
        "max_response_bytes": maximum_bytes,
        "preview_format": "partial-text",
        "preview_text": "",
    }
    overhead = serialized_size(envelope)
    envelope["preview_text"] = _utf8_prefix(raw, max(0, target - overhead - 64))
    while serialized_size(envelope) > target and envelope["preview_text"]:
        preview_size = len(envelope["preview_text"].encode("utf-8"))
        envelope["preview_text"] = _utf8_prefix(envelope["preview_text"], preview_size - 64)
    return envelope


def tool_result(data: dict[str, Any], summary: str, maximum_bytes: int) -> CallToolResult:
    bounded = bound_response(data, maximum_bytes)
    if bounded.get("preview_format") == "partial-text":
        summary = f"{summary} The machine-readable result is a bounded partial preview."
    return CallToolResult(
        content=[TextContent(type="text", text=summary[:1_000])],
        structuredContent=bounded,
    )


def error_result(message: str, *, code: str = "invalid_arguments") -> CallToolResult:
    safe = message[:500]
    return CallToolResult(
        content=[TextContent(type="text", text=f"Request failed: {safe}")],
        structuredContent={"error": {"code": code, "message": safe}},
        isError=True,
    )
