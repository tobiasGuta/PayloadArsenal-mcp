# PayloadArsenal-mcp

A small MCP (Model Context Protocol) server exposing search and read tools for a local payload/wordlist "arsenal" (e.g., PayloadsAllTheThings, SecLists).

## Features
- MCP tools:
  - `search_arsenal_files(query)`: find files by name under `/opt/arsenal`.
  - `read_arsenal_file(filepath, max_lines=500)`: safely read a file inside the arsenal.
  - `search_payload_content(query)`: grep Markdown payload files under `PayloadsAllTheThings`.

## Requirements
- Python 3.8 or newer
- See `requirements.txt` (the project depends on `mcp`)

## Install
1. (Optional) create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run locally
Start the MCP server directly:

```bash
python server.py
```

This runs the `FastMCP` server defined in `server.py` and uses `transport='stdio'` by default.

Clients that support the MCP standard (or a simple stdio bridge) can connect to this process and call the provided tools.

## Docker
Build the image (example):

```bash
docker build -t payload-arsenal-mcp .
```

Run the container and mount your local arsenal directory into the container at `/opt/arsenal`:

```bash
docker run --rm -it -v /absolute/path/to/your/arsenal:/opt/arsenal payload-arsenal-mcp
```

Notes:
- The server expects the arsenal files under `/opt/arsenal`. Mounting your payload collections into that path allows the MCP tools to search and read them.
- On Windows, use a full path for the host side of `-v` (for example `C:\Users\you\arsenal`).

## Example usage
From an MCP-capable client, call the tool names above with textual arguments. Example tool names:

- `search_arsenal_files("xss")` — returns matching file paths.
- `read_arsenal_file("/opt/arsenal/PayloadsAllTheThings/SomeFile.md")` — returns file contents (truncated by default).
- `search_payload_content("alert(1)")` — searches payload contents (limited results).

## Configuration
- `ARSENAL_DIR` is set in `server.py` (default `/opt/arsenal`). Change it there if you prefer a different path.

```bash
"payload_arsenal": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "payload-arsenal-mcp"
      ]
    }
```

## Troubleshooting
- If searches return no results, ensure your arsenal is mounted at `/opt/arsenal` and contains the payload collections (e.g., `PayloadsAllTheThings`, `SecLists`).
- Ensure the container or process has permission to read the files.

## License
See project or organization licensing policies. No license file included by default.
