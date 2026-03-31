"""Centralised configuration -- no module-level side effects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Runtime settings for Spec-OS.

    All paths are resolved lazily so importing the module never touches the
    filesystem.
    """

    base_dir: Path = field(default_factory=lambda: Path("data"))
    embedding_dim: int = 384
    chunk_max_len: int = 500
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    def ensure_dirs(self) -> None:
        """Create output directories on demand (not at import time)."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def vectors_file(self) -> Path:
        return self.base_dir / "embeddings.npy"

    @property
    def faiss_index_file(self) -> Path:
        return self.base_dir / "faiss.index"


# Singleton -- callers may override fields before first use.
settings = Settings()
