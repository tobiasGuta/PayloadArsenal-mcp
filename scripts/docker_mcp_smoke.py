#!/usr/bin/env python3
"""Start the Docker image over stdio and smoke-test MCP list/status calls."""

from __future__ import annotations

import argparse
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(image: str) -> None:
    parameters = StdioServerParameters(command="docker", args=["run", "--rm", "-i", image])
    async with stdio_client(parameters) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        required = {"arsenal_search_files", "arsenal_read_file", "arsenal_status"}
        if not required.issubset(names):
            raise RuntimeError("required tools are missing")
        status = await session.call_tool("arsenal_status", {})
        if status.isError or not status.structuredContent:
            raise RuntimeError("status tool failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", default="payload-arsenal-mcp:ci")
    args = parser.parse_args()
    asyncio.run(smoke(args.image))
    print("Docker MCP smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
