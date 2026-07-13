from __future__ import annotations

import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import server
from service import ArsenalService

EXPECTED_TOOLS = {
    "arsenal_search_files",
    "arsenal_read_file",
    "arsenal_search_content",
    "arsenal_categories",
    "arsenal_find_payload_references",
    "arsenal_find_wordlists",
    "arsenal_collections",
    "arsenal_status",
}


@pytest.fixture(autouse=True)
def configured_server(monkeypatch, settings):
    monkeypatch.setattr(server, "SETTINGS", settings)
    monkeypatch.setattr(server, "service", ArsenalService(settings))


@pytest.mark.anyio
async def test_tool_listing_and_calls_have_structured_content(capsys):
    tools = await server.mcp.list_tools()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS

    searched = await server.mcp.call_tool("arsenal_search_files", {"query": "graphql"})
    assert searched.structuredContent["returned"] == 1
    assert searched.content[0].text

    read = await server.mcp.call_tool(
        "arsenal_read_file",
        {"relative_path": "PayloadsAllTheThings/XSS Injection/README.md", "max_lines": 2},
    )
    assert read.structuredContent["returned_lines"] == 2

    status = await server.mcp.call_tool("arsenal_status", {})
    assert status.structuredContent["server"]["version"] == "1.0.0"
    assert capsys.readouterr().out == ""


@pytest.mark.anyio
async def test_unexpected_arguments_are_rejected_by_mcp_schema():
    with pytest.raises(ToolError, match="Extra inputs are not permitted"):
        await server.mcp.call_tool("arsenal_status", {"unexpected": "value"})


def test_internal_error_is_logged_but_client_response_is_safe(monkeypatch, caplog):
    def explode(_payload):
        raise RuntimeError(f"secret traceback path: {server.SETTINGS.arsenal_root}")

    monkeypatch.setattr(server.service, "status", explode)
    with caplog.at_level("ERROR"):
        result = server.arsenal_status()
    encoded = json.dumps(result.structuredContent)
    assert result.isError is True
    assert "internal server error" in encoded.lower()
    assert str(server.SETTINGS.arsenal_root) not in encoded
    assert "Unhandled tool failure" in caplog.text
