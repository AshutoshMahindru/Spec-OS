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


# ── Fuzzy alias detection (Change B) ────────────────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def levenshtein_ratio(a: str, b: str) -> float:
    """Return a similarity ratio 0.0–1.0 between two strings."""
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - _levenshtein(a, b) / max_len


def find_possible_aliases(names: list[str], *, threshold: float = 0.8) -> list[tuple[str, str, float]]:
    """Find pairs of names that might be aliases of each other.

    Returns ``[(name_a, name_b, similarity), ...]`` for pairs above *threshold*.
    Also flags substring relationships regardless of edit distance.
    """
    pairs: list[tuple[str, str, float]] = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a == b:
                continue
            # Substring check.
            if a in b or b in a:
                pairs.append((a, b, 1.0))
                continue
            ratio = levenshtein_ratio(a, b)
            if ratio >= threshold:
                pairs.append((a, b, round(ratio, 3)))
    return pairs
