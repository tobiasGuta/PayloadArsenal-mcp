# PayloadArsenal-mcp 1.0.0

PayloadArsenal-mcp is a read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for finding and retrieving bounded reference material from local security collections. It operates generically over the mounted arsenal and supports bundled snapshots of PayloadsAllTheThings and SecLists plus additional user-mounted collections.

The server retrieves references; it does not test targets. It has no target-network client, scanner, exploit runner, payload injector, reverse-shell generator, or command-execution tool. Payload examples are returned only when they already exist in a local source collection. Review all retrieved material before authorized use. A returned payload does not prove a vulnerability.

## Security boundary

MCP arguments are untrusted. Every file reference must be relative to `ARSENAL_DIR`; absolute paths, traversal, control characters, escaping symlinks, directories, unsupported extensions, and binary files are rejected. Containment uses resolved paths and `os.path.commonpath`, not string prefixes. Searches use Python and SQLite APIs only—no user input reaches a shell or subprocess. Arsenal files are never written.

Readable extensions are `.md`, `.txt`, `.lst`, `.list`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.conf`, and `.ini`. Source code, archives, executables, binaries, and unknown formats are not readable.

All successful calls contain concise MCP text `content` and machine-readable `structuredContent`. Shared UTF-8 byte bounding replaces an oversized structure with valid truncation metadata and a partial-text preview; it never emits truncated JSON as if it were valid JSON. Client errors are controlled, while detailed diagnostics go only to stderr.

## Tools

| Tool | Purpose |
| --- | --- |
| `arsenal_search_files` | Deterministically rank supported files by filename and relative-path match. |
| `arsenal_read_file` | Stream a bounded numbered line range from a supported text file. |
| `arsenal_search_content` | Search supported text with line numbers, context, scores, and SQLite FTS fallback. |
| `arsenal_categories` | Discover categories from real directories and Markdown headings. |
| `arsenal_find_payload_references` | Retrieve short source-derived payload or methodology passages without generating or executing anything. |
| `arsenal_find_wordlists` | Return advisory wordlist metadata, not full wordlist contents. |
| `arsenal_collections` | Return safe collection availability, counts, repository, and revision metadata. |
| `arsenal_status` | Return version, validated safe settings, index status, and available-collection count. |

### Tool examples

Arguments below are the JSON objects sent in MCP `tools/call` requests.

```json
{"query":"graphql","collection":"SecLists","extensions":[".txt",".md"],"limit":20}
```

```json
{"relative_path":"PayloadsAllTheThings/XSS Injection/README.md","start_line":100,"end_line":180}
```

Alternatively, use `"max_lines": 200` instead of `end_line`; the two range modes cannot be combined.

```json
{"query":"UNION SELECT","collection":"PayloadsAllTheThings","extensions":[".md"],"case_sensitive":false,"limit":25,"context_lines":2}
```

```json
{"collection":"PayloadsAllTheThings","depth":2,"limit":100}
```

```json
{"vulnerability_class":"xss","context":"html_attribute","constraints":["double quotes filtered"],"collection":"PayloadsAllTheThings","limit":15}
```

The payload-reference result labels source passages, collection revisions, paths, and line ranges. If no source-derived payload is found, it returns relevant methodology passages or an empty result—it does not invent a payload.

```json
{"purpose":"api endpoint discovery","technology":"graphql","collection":"SecLists","maximum_files":10,"maximum_size_bytes":500000}
```

Wordlist ranking is advisory and does not claim that a list is optimal or complete.

```json
{}
```

The empty object calls `arsenal_collections`; the same input calls `arsenal_status` when that tool name is selected.

## Configuration

Invalid, malformed, or out-of-range values fall back to the documented safe default. Only validated numbers, booleans, the arsenal root basename, and collection names can appear in status output; index and host paths are not exposed.

| Variable | Default | Accepted range or values |
| --- | ---: | --- |
| `ARSENAL_DIR` | `/opt/arsenal` | Local arsenal root; file arguments remain relative to it |
| `ARSENAL_MAX_RESPONSE_BYTES` | `524288` | 16 KiB–4 MiB |
| `ARSENAL_MAX_FILE_BYTES` | `2097152` | 16 KiB–64 MiB |
| `ARSENAL_DEFAULT_READ_LINES` | `200` | 1–1000 and capped by max read lines |
| `ARSENAL_MAX_READ_LINES` | `1000` | 1–10000 |
| `ARSENAL_MAX_SEARCH_RESULTS` | `50` | 1–500 |
| `ARSENAL_SEARCH_TIMEOUT_SECONDS` | `10` | 1–120 |
| `ARSENAL_INDEX_ENABLED` | `true` | `true/false`, `1/0`, `yes/no`, or `on/off` |
| `ARSENAL_INDEX_PATH` | `/tmp/payload-arsenal-index.sqlite3` | Local SQLite path; never returned to clients |
| `ARSENAL_MAX_QUERY_LENGTH` | `500` | 1–2000 |

## Run locally

Python 3.11 or newer is required.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
ARSENAL_DIR=/absolute/path/to/arsenal python server.py
```

The server uses stdio transport. Do not write debugging output to stdout; diagnostics are logged to stderr.

## Connect from MCP clients

Use absolute paths and keep `ARSENAL_DIR` pointed at a local, read-only collection directory. The native Python examples assume dependencies were installed into this repository's `.venv`; substitute your actual paths. On Windows, quote paths that contain spaces and use `.venv\Scripts\python.exe`.

### Codex CLI

Add the native server to the active Codex CLI profile:

```bash
codex mcp add payload-arsenal \
  --env ARSENAL_DIR=/absolute/path/to/arsenal \
  -- /absolute/path/to/PayloadArsenal-mcp/.venv/bin/python \
     /absolute/path/to/PayloadArsenal-mcp/server.py

codex mcp list
```

PowerShell example:

```powershell
codex mcp add payload-arsenal `
  --env ARSENAL_DIR="C:\path\to\arsenal" `
  -- "C:\path\to\PayloadArsenal-mcp\.venv\Scripts\python.exe" `
     "C:\path\to\PayloadArsenal-mcp\server.py"

codex mcp list
```

To use the hardened container instead, replace the command after `--` with the Docker invocation below. It preserves the read-only filesystem, dropped capabilities, no-new-privileges setting, and read-only arsenal mount:

```bash
codex mcp add payload-arsenal -- \
  docker run --rm -i \
    --read-only \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    --tmpfs /tmp:rw,noexec,nosuid,size=128m \
    -v /absolute/path/to/arsenal:/opt/arsenal:ro \
    payload-arsenal-mcp:1.0.0
```

Remove it later with `codex mcp remove payload-arsenal`.

### Claude Code

Claude Code also supports local stdio MCP servers. The following creates a user-scoped entry; use `--scope project` only when the team intentionally wants to share an `.mcp.json` configuration.

```bash
claude mcp add payload-arsenal --scope user \
  --env ARSENAL_DIR=/absolute/path/to/arsenal \
  -- /absolute/path/to/PayloadArsenal-mcp/.venv/bin/python \
     /absolute/path/to/PayloadArsenal-mcp/server.py

claude mcp list
```

See the [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp) for client installation, scopes, and platform-specific behavior.

### Other compatible stdio clients

Many MCP clients accept an equivalent JSON object. Add it to that client's documented MCP configuration file, adjusting the executable and paths for the platform:

```json
{
  "mcpServers": {
    "payload-arsenal": {
      "command": "/absolute/path/to/PayloadArsenal-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/PayloadArsenal-mcp/server.py"],
      "env": {
        "ARSENAL_DIR": "/absolute/path/to/arsenal"
      }
    }
  }
}
```

Do not configure this server as an HTTP endpoint: it intentionally uses stdio and does not expose a network port. Restart or reload the client after changing its MCP configuration.

## Docker

The Dockerfile pins Python 3.13.14 by OCI digest, installs the hash-locked dependency graph, bundles collection snapshots at the commits recorded in `config/collections.json`, removes build-time Git metadata, runs as UID/GID 10001, exposes no port, and uses an exec-form stdio entrypoint.

```bash
docker build -t payload-arsenal-mcp:1.0.0 .
docker run --rm -i \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  payload-arsenal-mcp:1.0.0
```

Replace the bundled snapshots with any local arsenal using a read-only mount:

```bash
docker run --rm -i \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  -v /absolute/path/to/arsenal:/opt/arsenal:ro \
  payload-arsenal-mcp:1.0.0
```

Do not mount the arsenal writable. The only expected writable location is `/tmp` for an explicitly created index.

## Optional local index

SQLite FTS5 indexing is optional and local. The server never rebuilds it in the background or on a request. Unsupported, binary, and oversized files are skipped, and build file/time caps are enforced. A disabled, missing, unavailable, or corrupt index falls back to bounded direct search.

```bash
ARSENAL_DIR=/absolute/path/to/arsenal python scripts/build_index.py --max-files 100000 --timeout-seconds 900
python scripts/check_index.py
```

Index writes go only to `ARSENAL_INDEX_PATH`, never into a collection. Index rows include collection, relative path, filename, extension, headings, bounded content, file metadata, and the configured collection revision.

## Provenance and bundled collections

`config/collections.json` is the single source for bundled repository URLs and immutable revisions. Search, read, category, reference, wordlist, collection, and index records include collection provenance where applicable. An externally mounted collection not listed there is marked `unmanaged`; the server does not inspect `.git` or execute Git commands at runtime.

PayloadsAllTheThings and SecLists retain their own licenses. Their content is not relicensed under this project's MIT license.

## Architecture

- `server.py` contains only MCP registration, safe error handling, and stdio startup.
- `config.py` centralizes validated settings and limits.
- `schemas.py` strictly rejects malformed and unexpected inputs.
- `paths.py`, `readers.py`, and `responses.py` isolate containment, bounded reading, binary detection, and response limits.
- `search.py`, `categories.py`, `references.py`, and `wordlists.py` implement generic retrieval and ranking over actual mounted content.
- `indexing.py` provides explicit SQLite FTS5 build/search with safe fallback.
- `provenance.py` reads shared revision metadata and produces safe collection inventory.
- `service.py` composes all operations and adds provenance.

No production module contains target domains, exploit results, technology-to-payload mappings, vulnerability-to-payload tables, or copied collection payloads.

## Development and testing

```bash
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
pytest --cov=. --cov-report=term-missing
docker build -t payload-arsenal-mcp:ci .
python scripts/docker_mcp_smoke.py payload-arsenal-mcp:ci
```

CI runs formatting, linting, unit/in-process MCP integration tests, a Docker build, and a real stdio MCP smoke test with minimal `contents: read` permissions.

## Known limitations

- Relevance scores are transparent lexical heuristics, not evidence that a reference or wordlist is correct for a target.
- Direct content search skips files larger than `ARSENAL_MAX_FILE_BYTES`; bounded line reading can safely stream a small range from a larger text file.
- Binary detection is a bounded heuristic. The extension allowlist remains the first gate.
- The FTS index is a point-in-time local snapshot and must be rebuilt explicitly after collections change.
- Collection file counts may be expensive for extremely large mounts; search timeouts and result caps do not make filesystem enumeration constant-time.
- The server deliberately omits target networking, scanning, exploitation, payload generation, file execution, arbitrary writes, and automatic collection/index updates.

## License

Project code is released under the [MIT License](LICENSE). Bundled or mounted arsenal collections are separate works governed by their respective licenses.
