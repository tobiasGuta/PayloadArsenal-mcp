"""Optional local SQLite FTS5 index with safe direct-search fallback."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from os.path import commonpath

from config import Settings
from paths import ArsenalError, split_collection
from provenance import revision_for
from readers import is_probably_binary
from search import iter_supported_files

SCHEMA_VERSION = "1"


class ArsenalIndex:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.index_path

    def _connect(self, *, writable: bool = False) -> sqlite3.Connection:
        if writable:
            try:
                inside_arsenal = commonpath((str(self.settings.arsenal_root), str(self.path))) == str(
                    self.settings.arsenal_root
                )
            except ValueError:
                inside_arsenal = False
            if inside_arsenal:
                raise ArsenalError("index path cannot be inside the arsenal root")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=2)
        else:
            connection = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        return connection

    def available(self) -> bool:
        if not self.settings.index_enabled or not self.path.is_file():
            return False
        try:
            with closing(self._connect()) as connection:
                connection.execute("SELECT count(*) FROM documents").fetchone()
            return True
        except (OSError, sqlite3.Error):
            return False

    def status(self) -> dict[str, object]:
        result: dict[str, object] = {"available": False, "document_count": 0, "last_built_at": None}
        if not self.available():
            return result
        try:
            with closing(self._connect()) as connection:
                result["document_count"] = int(connection.execute("SELECT count(*) FROM documents").fetchone()[0])
                rows = dict(connection.execute("SELECT key, value FROM index_metadata").fetchall())
                result["last_built_at"] = rows.get("last_built_at")
                result["schema_version"] = rows.get("schema_version")
                result["available"] = True
        except sqlite3.Error:
            pass
        return result

    def build(self, *, max_files: int = 100_000, timeout_seconds: int = 900) -> dict[str, object]:
        started = time.monotonic()
        indexed = 0
        skipped = 0
        timed_out = False
        with closing(self._connect(writable=True)) as connection:
            connection.executescript(
                """
                DROP TABLE IF EXISTS documents;
                CREATE VIRTUAL TABLE documents USING fts5(
                    collection UNINDEXED, relative_path UNINDEXED, filename,
                    extension UNINDEXED, headings, content,
                    size_bytes UNINDEXED, mtime_ns UNINDEXED, revision UNINDEXED,
                    tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS index_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                DELETE FROM index_metadata;
                """
            )
            for path in iter_supported_files(self.settings):
                if indexed + skipped >= max_files or time.monotonic() - started > timeout_seconds:
                    timed_out = True
                    break
                try:
                    stat = path.stat()
                    if stat.st_size > self.settings.max_file_bytes or is_probably_binary(path):
                        skipped += 1
                        continue
                    content = path.read_text(encoding="utf-8", errors="replace")
                    headings = "\n".join(line.lstrip("# ") for line in content.splitlines() if line.startswith("#"))
                    collection, relative = split_collection(self.settings, path)
                    connection.execute(
                        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            collection,
                            relative,
                            path.name,
                            path.suffix.lower(),
                            headings,
                            content,
                            stat.st_size,
                            stat.st_mtime_ns,
                            revision_for(collection),
                        ),
                    )
                    indexed += 1
                except (OSError, UnicodeError):
                    skipped += 1
            built_at = datetime.now(UTC).isoformat()
            metadata = {
                "schema_version": SCHEMA_VERSION,
                "last_built_at": built_at,
                "document_count": str(indexed),
                "skipped_count": str(skipped),
            }
            connection.executemany("INSERT INTO index_metadata(key, value) VALUES (?, ?)", metadata.items())
            connection.commit()
        return {"indexed": indexed, "skipped": skipped, "timed_out": timed_out, "last_built_at": built_at}

    def search_content(
        self,
        query: str,
        *,
        collection: str | None,
        extensions: frozenset[str],
        limit: int,
        context_lines: int,
    ) -> dict[str, object] | None:
        if not self.available():
            return None
        phrase = '"' + query.replace('"', '""') + '"'
        candidates: list[sqlite3.Row]
        try:
            with closing(self._connect()) as connection:
                candidates = connection.execute(
                    "SELECT collection, relative_path, filename, extension, content, bm25(documents) AS rank "
                    "FROM documents WHERE documents MATCH ? ORDER BY rank, relative_path LIMIT ?",
                    (phrase, max(limit * 5, 50)),
                ).fetchall()
        except sqlite3.Error:
            return None

        results: list[dict[str, object]] = []
        needle = query.casefold()
        seen: set[tuple[str, int, str]] = set()
        for row in candidates:
            if collection is not None and row["collection"] != collection:
                continue
            if row["extension"] not in extensions:
                continue
            lines = str(row["content"]).splitlines()
            for index, text in enumerate(lines):
                if needle not in text.casefold():
                    continue
                identity = (str(row["relative_path"]), index + 1, text)
                if identity in seen:
                    continue
                seen.add(identity)
                results.append(
                    {
                        "collection": row["collection"],
                        "relative_path": row["relative_path"],
                        "line": index + 1,
                        "matched_text": text,
                        "context_before": lines[max(0, index - context_lines) : index],
                        "context_after": lines[index + 1 : index + context_lines + 1],
                        "score": round(max(0.0, min(1.0, 1.0 / (1.0 + abs(float(row["rank"]))))), 3),
                    }
                )
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        return {
            "query": query,
            "count": len(results),
            "returned": len(results),
            "truncated": len(results) >= limit,
            "timed_out": False,
            "search_backend": "sqlite-fts5",
            "results": results,
        }
