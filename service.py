"""Application service composing validated read-only retrieval operations."""

from __future__ import annotations

from typing import Any

from categories import discover_categories
from config import SERVER_NAME, VERSION, Settings
from indexing import ArsenalIndex
from provenance import add_provenance, collection_inventory
from readers import read_line_range
from references import find_payload_references
from schemas import (
    CategoriesRequest,
    CollectionsRequest,
    PayloadReferencesRequest,
    ReadFileRequest,
    SearchContentRequest,
    SearchFilesRequest,
    StatusRequest,
    WordlistsRequest,
    parse_request,
    validate_extensions,
)
from search import search_content, search_files
from wordlists import find_wordlists


class ArsenalService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.index = ArsenalIndex(settings)

    def _provenance(self, data: dict[str, Any]) -> dict[str, Any]:
        return add_provenance(data)

    def search_files(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(SearchFilesRequest, payload, self.settings)
        assert isinstance(request, SearchFilesRequest)
        result = search_files(
            self.settings,
            request.query.strip(),
            collection=request.collection,
            extensions=validate_extensions(request.extensions, self.settings),
            limit=request.limit,
        )
        return self._provenance(result)

    def read_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(ReadFileRequest, payload, self.settings)
        assert isinstance(request, ReadFileRequest)
        result = read_line_range(
            self.settings,
            request.relative_path,
            start_line=request.start_line,
            end_line=request.end_line,
            max_lines=request.max_lines,
        )
        return self._provenance(result)

    def search_content(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(SearchContentRequest, payload, self.settings)
        assert isinstance(request, SearchContentRequest)
        result = search_content(
            self.settings,
            request.query.strip(),
            collection=request.collection,
            extensions=validate_extensions(request.extensions, self.settings),
            case_sensitive=request.case_sensitive,
            limit=request.limit,
            context_lines=request.context_lines,
            index=self.index,
        )
        return self._provenance(result)

    def categories(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(CategoriesRequest, payload, self.settings)
        assert isinstance(request, CategoriesRequest)
        return self._provenance(
            discover_categories(self.settings, collection=request.collection, depth=request.depth, limit=request.limit)
        )

    def payload_references(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(PayloadReferencesRequest, payload, self.settings)
        assert isinstance(request, PayloadReferencesRequest)
        result = find_payload_references(
            self.settings,
            vulnerability_class=request.vulnerability_class.strip(),
            context=request.context.strip() if request.context else None,
            constraints=[item.strip() for item in request.constraints],
            collection=request.collection,
            limit=request.limit,
        )
        return self._provenance(result)

    def wordlists(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = parse_request(WordlistsRequest, payload, self.settings)
        assert isinstance(request, WordlistsRequest)
        result = find_wordlists(
            self.settings,
            purpose=request.purpose.strip(),
            technology=request.technology.strip() if request.technology else None,
            collection=request.collection,
            maximum_files=request.maximum_files,
            maximum_size_bytes=request.maximum_size_bytes,
        )
        return self._provenance(result)

    def collections(self, payload: dict[str, Any]) -> dict[str, Any]:
        parse_request(CollectionsRequest, payload, self.settings)
        return collection_inventory(self.settings)

    def status(self, payload: dict[str, Any]) -> dict[str, Any]:
        parse_request(StatusRequest, payload, self.settings)
        inventory = collection_inventory(self.settings)
        return {
            "server": {"name": SERVER_NAME, "version": VERSION},
            "configuration": self.settings.safe_public(),
            "index": self.index.status(),
            "collections": {"available": sum(bool(item["available"]) for item in inventory["collections"])},
        }
