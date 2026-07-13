from __future__ import annotations

import json

from config import Settings
from responses import bound_response, serialized_size, tool_result


def test_invalid_environment_values_fall_back(tmp_path):
    settings = Settings.from_env(
        {
            "ARSENAL_DIR": str(tmp_path),
            "ARSENAL_MAX_RESPONSE_BYTES": "nope",
            "ARSENAL_MAX_FILE_BYTES": "1",
            "ARSENAL_INDEX_ENABLED": "maybe",
        }
    )
    assert settings.max_response_bytes == 524_288
    assert settings.max_file_bytes == 2_097_152
    assert settings.index_enabled is True


def test_index_is_disabled_when_configured_inside_arsenal(tmp_path):
    settings = Settings.from_env(
        {
            "ARSENAL_DIR": str(tmp_path),
            "ARSENAL_INDEX_PATH": str(tmp_path / "index.sqlite3"),
        }
    )
    assert settings.index_enabled is False


def test_response_bound_is_valid_json_and_utf8_safe():
    data = {"results": ["🚀" * 2000], "truncated": False}
    result = bound_response(data, 16_384)
    encoded = json.dumps(result, ensure_ascii=False).encode("utf-8")
    encoded.decode("utf-8")
    assert serialized_size(result) < 16_384


def test_large_response_has_truncation_metadata():
    result = bound_response({"content": "x" * 50_000}, 16_384)
    assert result["truncated"] is True
    assert result["preview_format"] == "partial-text"
    assert result["original_response_bytes"] > result["max_response_bytes"]


def test_complete_mcp_result_stays_below_byte_ceiling():
    result = tool_result({"content": "🚀" * 20_000}, "Bounded response", 16_384)
    assert len(result.model_dump_json(by_alias=True).encode("utf-8")) < 16_384
