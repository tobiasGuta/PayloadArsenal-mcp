"""Strict input schemas shared by MCP handlers and unit tests."""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from config import Settings
from paths import ArsenalError


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchFilesRequest(StrictRequest):
    query: str
    collection: str | None = None
    extensions: list[str] | None = Field(default=None, max_length=20)
    limit: StrictInt = 20


class ReadFileRequest(StrictRequest):
    relative_path: str
    start_line: StrictInt = 1
    end_line: StrictInt | None = None
    max_lines: StrictInt | None = None

    @model_validator(mode="after")
    def validate_range_mode(self) -> ReadFileRequest:
        if self.end_line is not None and self.max_lines is not None:
            raise ValueError("end_line and max_lines cannot both be supplied")
        if self.start_line < 1:
            raise ValueError("start_line must be at least 1")
        if self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class SearchContentRequest(StrictRequest):
    query: str
    collection: str | None = None
    extensions: list[str] | None = Field(default=None, max_length=20)
    case_sensitive: StrictBool = False
    limit: StrictInt = 25
    context_lines: StrictInt = 0

    @field_validator("context_lines")
    @classmethod
    def validate_context(cls, value: int) -> int:
        if not 0 <= value <= 5:
            raise ValueError("context_lines must be between 0 and 5")
        return value


class CategoriesRequest(StrictRequest):
    collection: str | None = None
    depth: StrictInt = 2
    limit: StrictInt = 100

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("depth must be between 1 and 5")
        return value


class PayloadReferencesRequest(StrictRequest):
    vulnerability_class: str
    context: str | None = None
    constraints: list[str] = Field(default_factory=list, max_length=20)
    collection: str | None = None
    limit: StrictInt = 15

    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 500 for value in values):
            raise ValueError("constraints must be nonempty strings of at most 500 characters")
        return values


class WordlistsRequest(StrictRequest):
    purpose: str
    technology: str | None = None
    collection: str | None = None
    maximum_files: StrictInt = 10
    maximum_size_bytes: StrictInt | None = None

    @field_validator("maximum_size_bytes")
    @classmethod
    def validate_size(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("maximum_size_bytes must be positive")
        return value


class CollectionsRequest(StrictRequest):
    pass


class StatusRequest(StrictRequest):
    pass


def _validate_text(value: str | None, label: str, settings: Settings, *, required: bool = False) -> None:
    if value is None:
        if required:
            raise ArsenalError(f"{label} is required")
        return
    if not isinstance(value, str) or (required and not value.strip()):
        raise ArsenalError(f"{label} must be a nonempty string")
    if len(value) > settings.max_query_length:
        raise ArsenalError(f"{label} exceeds the configured maximum length")
    if "\x00" in value or any(ord(char) < 32 and char not in {"\t", "\n", "\r"} for char in value):
        raise ArsenalError(f"{label} contains prohibited characters")


def validate_extensions(extensions: list[str] | None, settings: Settings) -> frozenset[str]:
    if extensions is None:
        return settings.supported_extensions
    normalized: set[str] = set()
    for extension in extensions:
        if not isinstance(extension, str):
            raise ArsenalError("extensions must contain strings")
        value = extension.lower()
        if not value.startswith("."):
            value = f".{value}"
        if value not in settings.supported_extensions:
            raise ArsenalError(f"unsupported extension: {value}")
        normalized.add(value)
    return frozenset(normalized)


def parse_request(model: type[StrictRequest], payload: dict[str, Any], settings: Settings) -> StrictRequest:
    try:
        request = model.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first["loc"])
        raise ArsenalError(f"invalid {location or 'arguments'}: {first['msg']}") from None

    for field in ("query", "purpose", "vulnerability_class"):
        if hasattr(request, field):
            _validate_text(getattr(request, field), field, settings, required=True)
    for field in ("context", "technology"):
        if hasattr(request, field):
            _validate_text(getattr(request, field), field, settings)

    limit = getattr(request, "limit", getattr(request, "maximum_files", None))
    if limit is not None and not 1 <= limit <= settings.max_search_results:
        raise ArsenalError("result limit is outside the configured range")
    if isinstance(request, ReadFileRequest):
        requested = request.max_lines
        if requested is not None and not 1 <= requested <= settings.max_read_lines:
            raise ArsenalError("max_lines is outside the configured range")
        if request.end_line is not None and request.end_line - request.start_line + 1 > settings.max_read_lines:
            raise ArsenalError("requested line range exceeds the configured maximum")
    return request
