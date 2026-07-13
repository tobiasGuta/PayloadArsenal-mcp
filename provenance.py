"""Shared collection provenance and safe collection statistics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import Settings
from paths import collection_names

METADATA_PATH = Path(__file__).with_name("config") / "collections.json"


def load_collection_metadata(path: Path = METADATA_PATH) -> dict[str, dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        collections = raw.get("collections", {})
        if not isinstance(collections, dict):
            return {}
        return {
            str(name): {
                "repository": str(value.get("repository", "")),
                "revision": str(value.get("revision", "unknown")),
            }
            for name, value in collections.items()
            if isinstance(value, dict)
        }
    except (OSError, ValueError, TypeError):
        return {}


def revision_for(collection: str, metadata: dict[str, dict[str, str]] | None = None) -> str:
    source = metadata if metadata is not None else load_collection_metadata()
    return source.get(collection, {}).get("revision", "unmanaged")


def collection_inventory(settings: Settings) -> dict[str, Any]:
    metadata = load_collection_metadata()
    results: list[dict[str, object]] = []
    for name in sorted(set(collection_names(settings)) | set(metadata), key=str.casefold):
        path = settings.arsenal_root / name
        available = path.is_dir()
        file_count = 0
        supported_count = 0
        if available:
            for candidate in path.rglob("*"):
                try:
                    if candidate.is_file():
                        file_count += 1
                        if candidate.suffix.lower() in settings.supported_extensions:
                            supported_count += 1
                except OSError:
                    continue
        configured = metadata.get(name, {})
        item: dict[str, object] = {
            "name": name,
            "available": available,
            "revision": configured.get("revision", "unmanaged"),
            "file_count": file_count,
            "supported_text_files": supported_count,
        }
        if configured.get("repository"):
            item["repository"] = configured["repository"]
        results.append(item)
    return {"collections": results}


def add_provenance(value: Any, metadata: dict[str, dict[str, str]] | None = None) -> Any:
    """Attach safe revision provenance to nested result records in place."""
    source = metadata if metadata is not None else load_collection_metadata()
    if isinstance(value, list):
        for item in value:
            add_provenance(item, source)
    elif isinstance(value, dict):
        collection = value.get("collection")
        if isinstance(collection, str) and collection and "source" not in value:
            configured = source.get(collection, {})
            value["source"] = {"collection_revision": configured.get("revision", "unmanaged")}
        for nested in value.values():
            add_provenance(nested, source)
    return value
