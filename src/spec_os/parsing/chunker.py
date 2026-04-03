"""Split structured sections into overlapping-free text chunks."""

from __future__ import annotations

from spec_os.config import settings
from spec_os.helpers import normalize_text


def chunk_text(
    sections: list[dict],
    doc_id: str,
    max_len: int | None = None,
) -> list[dict]:
    """Produce ``[{doc_id, text, heading}, ...]`` chunks from sections."""
    max_len = max_len or settings.chunk_max_len
    chunks: list[dict] = []
    buffer = ""
    heading = ""

    for sec in sections:
        if sec.get("type") == "heading":
            if buffer:
                chunks.append({"doc_id": doc_id, "text": buffer.strip(), "heading": heading})
                buffer = ""
            heading = normalize_text(sec.get("text", ""))
            continue

        text = normalize_text(sec.get("text", ""))
        if not text:
            continue

        if len(buffer) + len(text) + 1 < max_len:
            buffer = f"{buffer} {text}".strip()
        else:
            if buffer:
                chunks.append({"doc_id": doc_id, "text": buffer.strip(), "heading": heading})
            buffer = text

    if buffer:
        chunks.append({"doc_id": doc_id, "text": buffer.strip(), "heading": heading})

    return chunks
