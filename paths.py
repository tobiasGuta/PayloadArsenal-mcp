"""Path containment and collection discovery primitives."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from config import Settings


class ArsenalError(ValueError):
    """A controlled error that is safe to present to an MCP client."""


def _reject_unsafe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ArsenalError(f"{label} must be a nonempty string")
    if "\x00" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ArsenalError(f"{label} contains prohibited characters")


def normalize_relative_path(relative_path: str) -> PurePosixPath:
    _reject_unsafe_text(relative_path, "relative_path")
    normalized = relative_path.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(relative_path)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        raise ArsenalError("absolute paths are not permitted")
    if any(part in {"..", ""} for part in posix.parts):
        raise ArsenalError("path traversal is not permitted")
    return posix


def _contained(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError:
        return False


def resolve_under_root(
    settings: Settings,
    relative_path: str,
    *,
    require_file: bool = True,
    require_supported: bool = True,
) -> Path:
    relative = normalize_relative_path(relative_path)
    root = settings.arsenal_root.resolve()
    candidate = root.joinpath(*relative.parts).resolve()
    if not _contained(root, candidate):
        raise ArsenalError("path resolves outside the arsenal root")
    if not candidate.exists():
        raise ArsenalError("requested path does not exist")
    if require_file and not candidate.is_file():
        raise ArsenalError("requested path is not a file")
    if not require_file and not candidate.is_dir():
        raise ArsenalError("requested path is not a directory")
    if require_supported and candidate.suffix.lower() not in settings.supported_extensions:
        raise ArsenalError("file type is not supported")
    return candidate


def safe_relative(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not _contained(resolved_root, resolved_path):
        raise ArsenalError("path resolves outside the arsenal root")
    return resolved_path.relative_to(resolved_root).as_posix()


def collection_names(settings: Settings) -> list[str]:
    root = settings.arsenal_root
    if not root.is_dir():
        return []
    names: list[str] = []
    for child in root.iterdir():
        try:
            if child.is_dir() and _contained(root.resolve(), child.resolve()):
                names.append(child.name)
        except OSError:
            continue
    return sorted(names, key=str.casefold)


def resolve_collection(settings: Settings, collection: str | None) -> tuple[Path, str | None]:
    if collection is None:
        return settings.arsenal_root, None
    _reject_unsafe_text(collection, "collection")
    if "/" in collection or "\\" in collection or collection in {".", ".."}:
        raise ArsenalError("collection must be a direct child name")
    path = resolve_under_root(settings, collection, require_file=False, require_supported=False)
    return path, path.name


def split_collection(settings: Settings, path: Path) -> tuple[str, str]:
    arsenal_relative = safe_relative(settings.arsenal_root, path)
    parts = PurePosixPath(arsenal_relative).parts
    collection = parts[0] if len(parts) > 1 else ""
    relative = PurePosixPath(*parts[1:]).as_posix() if len(parts) > 1 else parts[0]
    return collection, relative
