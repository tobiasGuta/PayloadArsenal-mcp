"""Centralized, validated runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VERSION = "1.0.0"
SERVER_NAME = "payload-arsenal-mcp"

SUPPORTED_EXTENSIONS = frozenset(
    {".md", ".txt", ".lst", ".list", ".csv", ".json", ".yaml", ".yml", ".xml", ".conf", ".ini"}
)


@dataclass(frozen=True)
class _IntegerSetting:
    env: str
    default: int
    minimum: int
    maximum: int


_INTEGER_SETTINGS = {
    "max_response_bytes": _IntegerSetting("ARSENAL_MAX_RESPONSE_BYTES", 524_288, 16_384, 4_194_304),
    "max_file_bytes": _IntegerSetting("ARSENAL_MAX_FILE_BYTES", 2_097_152, 16_384, 67_108_864),
    "default_read_lines": _IntegerSetting("ARSENAL_DEFAULT_READ_LINES", 200, 1, 1_000),
    "max_read_lines": _IntegerSetting("ARSENAL_MAX_READ_LINES", 1_000, 1, 10_000),
    "max_search_results": _IntegerSetting("ARSENAL_MAX_SEARCH_RESULTS", 50, 1, 500),
    "search_timeout_seconds": _IntegerSetting("ARSENAL_SEARCH_TIMEOUT_SECONDS", 10, 1, 120),
    "max_query_length": _IntegerSetting("ARSENAL_MAX_QUERY_LENGTH", 500, 1, 2_000),
}


def _safe_integer(source: dict[str, str], spec: _IntegerSetting) -> int:
    raw = source.get(spec.env)
    if raw is None:
        return spec.default
    try:
        value = int(raw, 10)
    except (TypeError, ValueError):
        return spec.default
    return value if spec.minimum <= value <= spec.maximum else spec.default


def _safe_bool(source: dict[str, str], name: str, default: bool) -> bool:
    raw = source.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_path(raw: str | None, default: str) -> Path:
    value = raw or default
    if "\x00" in value or any(ord(char) < 32 for char in value):
        value = default
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    arsenal_root: Path
    max_response_bytes: int
    max_file_bytes: int
    default_read_lines: int
    max_read_lines: int
    max_search_results: int
    search_timeout_seconds: int
    index_enabled: bool
    index_path: Path
    max_query_length: int
    supported_extensions: frozenset[str] = SUPPORTED_EXTENSIONS

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Settings:
        source = dict(os.environ if environ is None else environ)
        values = {name: _safe_integer(source, spec) for name, spec in _INTEGER_SETTINGS.items()}
        # A default read must never exceed the independently configured maximum.
        values["default_read_lines"] = min(values["default_read_lines"], values["max_read_lines"])
        arsenal_root = _safe_path(source.get("ARSENAL_DIR"), "/opt/arsenal")
        index_path = _safe_path(source.get("ARSENAL_INDEX_PATH"), "/tmp/payload-arsenal-index.sqlite3")
        index_enabled = _safe_bool(source, "ARSENAL_INDEX_ENABLED", True)
        try:
            if os.path.commonpath((str(arsenal_root), str(index_path))) == str(arsenal_root):
                index_enabled = False
        except ValueError:
            pass
        return cls(
            arsenal_root=arsenal_root,
            index_enabled=index_enabled,
            index_path=index_path,
            **values,
        )

    def safe_public(self) -> dict[str, object]:
        return {
            "arsenal_root_name": self.arsenal_root.name,
            "max_response_bytes": self.max_response_bytes,
            "max_file_bytes": self.max_file_bytes,
            "default_read_lines": self.default_read_lines,
            "max_read_lines": self.max_read_lines,
            "max_search_results": self.max_search_results,
            "search_timeout_seconds": self.search_timeout_seconds,
            "index_enabled": self.index_enabled,
            "max_query_length": self.max_query_length,
        }


SETTINGS = Settings.from_env()
