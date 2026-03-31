"""Optional embedding + vector-store layer.

All heavy imports (numpy, sentence-transformers, faiss) are guarded so the
rest of the package works without them.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Lazy imports ────────────────────────────────────────────────────────────

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    _HAS_ST = True
except ImportError:
    _HAS_ST = False
    SentenceTransformer = None  # type: ignore[assignment,misc]

try:
    import faiss  # type: ignore[import-untyped]

    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False
    faiss = None  # type: ignore[assignment]

# Lazy singleton – loaded on first call to ``embed_chunks``.
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None and _HAS_ST:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


# ── Public API ──────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict], dim: int = 384) -> list[dict]:
    """Return ``[{text, embedding}, ...]``.  *embedding* is ``None`` when numpy is unavailable."""
    if not chunks:
        return []
    if not _HAS_NUMPY:
        return [{"text": c.get("text", ""), "embedding": None} for c in chunks]

    texts = [c.get("text", "") for c in chunks]
    model = _get_embed_model()
    if model is not None:
        vectors = model.encode(texts)
    else:
        vectors = _deterministic_random_vectors(texts, dim)

    return [{"text": texts[i], "embedding": vec} for i, vec in enumerate(vectors)]


def store_embeddings(embeddings: list[dict], *, vectors_file: Path, index_file: Path, dim: int = 384) -> None:
    """Persist embeddings to numpy / FAISS. Params are now explicit (no globals)."""
    if not embeddings or not _HAS_NUMPY:
        return
    vectors = np.array(
        [e["embedding"] for e in embeddings if e.get("embedding") is not None],
        dtype="float32",
    )
    if len(vectors) == 0:
        return

    if _HAS_FAISS:
        try:
            index = faiss.IndexFlatL2(dim)
            index.add(vectors)
            faiss.write_index(index, str(index_file))
            return
        except Exception as exc:
            logger.warning("FAISS write failed: %s", exc)

    # Fallback to raw .npy
    if vectors_file.exists():
        existing = np.load(str(vectors_file))
        combined = np.vstack([existing, vectors])
    else:
        combined = vectors
    np.save(str(vectors_file), combined)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _deterministic_random_vectors(texts: list[str], dim: int):
    """Hash-seeded pseudo-random vectors for deterministic testing."""
    vecs = []
    for text in texts:
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vecs.append(rng.rand(dim).astype("float32"))
    return np.array(vecs)
