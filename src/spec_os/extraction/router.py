"""Router that dispatches to the right extractor based on doc_type."""

from __future__ import annotations

from spec_os.extraction.api_spec import extract_api_spec_graph
from spec_os.extraction.architecture import extract_architecture_graph
from spec_os.extraction.data_dictionary import extract_data_dictionary_graph
from spec_os.extraction.generic import extract_generic_graph
from spec_os.extraction.prd import extract_prd_graph
from spec_os.extraction.wireframe import extract_wireframe_graph

_ROUTER: dict[str, object] = {
    "PRD": extract_prd_graph,
    "ARCHITECTURE": extract_architecture_graph,
    "API_SPEC": extract_api_spec_graph,
    "DATA_DICTIONARY": extract_data_dictionary_graph,
    "WIREFRAME": extract_wireframe_graph,
}


def route_extraction(structured: list[dict], doc_id: str, doc_type: str) -> dict:
    """Dispatch to the type-specific extractor, or fall back to generic."""
    extractor = _ROUTER.get(doc_type, extract_generic_graph)
    return extractor(structured, doc_id)
