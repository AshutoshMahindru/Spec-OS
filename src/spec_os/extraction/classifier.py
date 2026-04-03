"""Classify a document by inspecting its structured sections."""

from __future__ import annotations


def classify_document(structured: list[dict]) -> str:
    """Return one of PRD, API_SPEC, DATA_DICTIONARY, ARCHITECTURE, WIREFRAME, GENERIC."""
    blob = " ".join(s.get("text", "").lower() for s in structured)

    if "product requirements document" in blob or "functional requirements" in blob or "mvp" in blob:
        return "PRD"
    if "base path:" in blob or "/api/" in blob or "jwt bearer token" in blob:
        return "API_SPEC"
    if "schema conventions" in blob or "total tables" in blob or "row-level security" in blob:
        return "DATA_DICTIONARY"
    if "layered architecture" in blob or "canonical engine flow" in blob or "architecture overview" in blob:
        return "ARCHITECTURE"
    if "dashboard" in blob or "screen tiers" in blob or "ux requirements" in blob:
        return "WIREFRAME"
    return "GENERIC"
