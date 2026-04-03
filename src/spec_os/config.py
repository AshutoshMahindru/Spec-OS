"""Centralised configuration -- no module-level side effects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    return values or default


@dataclass
class Settings:
    """Runtime settings for Spec-OS.

    All paths are resolved lazily so importing the module never touches the
    filesystem.
    """

    base_dir: Path = field(default_factory=lambda: Path(os.getenv("SPEC_OS_BASE_DIR", "data")))
    environment: str = field(default_factory=lambda: os.getenv("SPEC_OS_ENV", "local-dev"))
    debug_errors: bool = field(default_factory=lambda: _env_bool("SPEC_OS_DEBUG_ERRORS", False))
    enable_embeddings: bool = field(default_factory=lambda: _env_bool("SPEC_OS_ENABLE_EMBEDDINGS", False))
    embedding_backend: str = field(default_factory=lambda: os.getenv("SPEC_OS_EMBEDDING_BACKEND", "deterministic"))
    embedding_dim: int = field(default_factory=lambda: _env_int("SPEC_OS_EMBEDDING_DIM", 384))
    chunk_max_len: int = field(default_factory=lambda: _env_int("SPEC_OS_CHUNK_MAX_LEN", 500))
    server_host: str = field(default_factory=lambda: os.getenv("SPEC_OS_SERVER_HOST", "0.0.0.0"))
    server_port: int = field(default_factory=lambda: _env_int("SPEC_OS_SERVER_PORT", 8000))
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: _env_list(
            "SPEC_OS_ALLOWED_ORIGINS",
            ("http://localhost:3000", "http://127.0.0.1:3000"),
        )
    )
    max_upload_size_bytes: int = field(default_factory=lambda: _env_int("SPEC_OS_MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024))
    allowed_upload_extensions: tuple[str, ...] = field(
        default_factory=lambda: _env_list("SPEC_OS_ALLOWED_UPLOAD_EXTENSIONS", (".mhtml", ".mht"))
    )
    allowed_upload_content_types: tuple[str, ...] = field(
        default_factory=lambda: _env_list(
            "SPEC_OS_ALLOWED_UPLOAD_CONTENT_TYPES",
            ("multipart/related", "message/rfc822", "application/octet-stream"),
        )
    )

    def ensure_dirs(self) -> None:
        """Create output directories on demand (not at import time)."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def debug_mode(self) -> bool:
        return self.debug_errors or self.environment in {"local-dev", "test"}

    @property
    def normalized_upload_extensions(self) -> tuple[str, ...]:
        return tuple(ext if ext.startswith(".") else f".{ext}" for ext in self.allowed_upload_extensions)

    @property
    def vectors_file(self) -> Path:
        return self.base_dir / "embeddings.npy"

    @property
    def faiss_index_file(self) -> Path:
        return self.base_dir / "faiss.index"


# Singleton -- callers may override fields before first use.
settings = Settings()
