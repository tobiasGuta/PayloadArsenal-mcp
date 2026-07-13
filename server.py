"""Read-only Payload Arsenal Model Context Protocol server."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from pydantic import StrictBool, StrictInt, StrictStr

from config import SERVER_NAME, SETTINGS
from paths import ArsenalError
from responses import error_result, tool_result
from service import ArsenalService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger(SERVER_NAME)

mcp = FastMCP(SERVER_NAME, log_level="ERROR")
service = ArsenalService(SETTINGS)


def _invoke(operation: Callable[[], dict[str, Any]], summary: str) -> CallToolResult:
    try:
        data = operation()
        return tool_result(data, summary, SETTINGS.max_response_bytes)
    except ArsenalError as exc:
        return error_result(str(exc))
    except Exception:
        LOGGER.exception("Unhandled tool failure")
        return error_result("An internal server error occurred.", code="internal_error")


@mcp.tool()
def arsenal_search_files(
    query: StrictStr,
    collection: StrictStr | None = None,
    extensions: list[StrictStr] | None = None,
    limit: StrictInt = 20,
) -> CallToolResult:
    """Search supported files by filename and relative path."""
    arguments = locals()
    return _invoke(
        lambda: service.search_files(arguments),
        f"Searched arsenal file names for {query!r}.",
    )


@mcp.tool()
def arsenal_read_file(
    relative_path: StrictStr,
    start_line: StrictInt = 1,
    end_line: StrictInt | None = None,
    max_lines: StrictInt | None = None,
) -> CallToolResult:
    """Read a bounded, numbered line range from a supported text file."""
    arguments = locals()
    return _invoke(lambda: service.read_file(arguments), f"Read a bounded range from {relative_path!r}.")


@mcp.tool()
def arsenal_search_content(
    query: StrictStr,
    collection: StrictStr | None = None,
    extensions: list[StrictStr] | None = None,
    case_sensitive: StrictBool = False,
    limit: StrictInt = 25,
    context_lines: StrictInt = 0,
) -> CallToolResult:
    """Search supported local text files with line-numbered context."""
    arguments = locals()
    return _invoke(lambda: service.search_content(arguments), f"Searched arsenal content for {query!r}.")


@mcp.tool()
def arsenal_categories(
    collection: StrictStr | None = None,
    depth: StrictInt = 2,
    limit: StrictInt = 100,
) -> CallToolResult:
    """Discover categories from directories and Markdown headings."""
    arguments = locals()
    return _invoke(lambda: service.categories(arguments), "Discovered categories from the mounted collections.")


@mcp.tool()
def arsenal_find_payload_references(
    vulnerability_class: StrictStr,
    context: StrictStr | None = None,
    constraints: list[StrictStr] | None = None,
    collection: StrictStr | None = None,
    limit: StrictInt = 15,
) -> CallToolResult:
    """Retrieve existing source-derived payload and methodology passages; never generate or execute payloads."""
    arguments = locals()
    arguments["constraints"] = constraints or []
    return _invoke(
        lambda: service.payload_references(arguments),
        f"Retrieved source-derived references for {vulnerability_class!r}.",
    )


@mcp.tool()
def arsenal_find_wordlists(
    purpose: StrictStr,
    technology: StrictStr | None = None,
    collection: StrictStr | None = None,
    maximum_files: StrictInt = 10,
    maximum_size_bytes: StrictInt | None = None,
) -> CallToolResult:
    """Return advisory wordlist metadata without dumping wordlist contents."""
    arguments = locals()
    return _invoke(lambda: service.wordlists(arguments), f"Discovered wordlist candidates for {purpose!r}.")


@mcp.tool()
def arsenal_collections() -> CallToolResult:
    """Return safe availability, count, and pinned-revision collection metadata."""
    return _invoke(lambda: service.collections({}), "Inspected available arsenal collections.")


@mcp.tool()
def arsenal_status() -> CallToolResult:
    """Return safe server, validated configuration, collection, and index status."""
    return _invoke(lambda: service.status({}), "Inspected payload arsenal server status.")


def _harden_tool_input_models() -> None:
    """Make FastMCP's generated argument models and advertised schemas reject extras."""
    for registered in mcp._tool_manager._tools.values():
        registered.parameters["additionalProperties"] = False
        argument_model = registered.fn_metadata.arg_model
        argument_model.model_config["extra"] = "forbid"
        argument_model.model_rebuild(force=True)


_harden_tool_input_models()


if __name__ == "__main__":
    mcp.run(transport="stdio")
