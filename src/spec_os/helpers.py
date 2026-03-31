"""Shared low-level helpers used across modules."""

from __future__ import annotations

import re


def normalize_text(text: str | None) -> str:
    """Normalise unicode dashes and replacement chars to plain ASCII hyphen."""
    if not text:
        return text or ""
    text = text.replace("\uFFFD", "-")
    text = text.replace("\ufffd\ufffd\ufffd", "-")
    text = text.replace("\u2013", "-")   # en-dash
    text = text.replace("\u2014", "-")   # em-dash
    return text


def normalize_name(name: str | None) -> str:
    """Collapse a raw name into a canonical lower_snake form, applying ontology aliases."""
    from spec_os.constants import CANONICAL_ONTOLOGY  # deferred to avoid circular

    if not name:
        return name or ""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")

    for canonical, variants in CANONICAL_ONTOLOGY.items():
        if name in variants:
            return canonical
    return name


def safe_node_id(node_type: str, key_value: str) -> str:
    """Deterministic node-id from type + key value."""
    key_value = normalize_text(" ".join(str(key_value).split()))
    safe_key = re.sub(r"[^a-z0-9]+", "_", key_value.lower()).strip("_") or "unknown"
    return f"{node_type.lower()}_{safe_key}"
