"""Shared artifact writer / reader layer."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

JSON_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "structured": ("layers", "structured.json"),
    "graph": ("layers", "graph.json"),
    "graph_validation": ("validation", "graph_validation.json"),
    "canonical_model": ("canonical", "canonical_model.json"),
    "computation_validation": ("validation", "computation_validation.json"),
    "schema": ("domain", "schema.json"),
    "roadmap": ("artifacts", "roadmap.json"),
    "traceability": ("artifacts", "traceability.json"),
    "computation_graph": ("domain", "computation_graph.json"),
    "api_contracts": ("domain", "api_contracts.json"),
    "variable_registry": ("canonical", "variable_registry.json"),
    "canonical_schema": ("domain", "canonical_schema.json"),
    "reconciliation": ("validation", "reconciliation.json"),
    "variable_mapping": ("system", "variable_mapping.json"),
    "execution_plan": ("system", "execution_plan.json"),
    "api_bindings": ("system", "api_bindings.json"),
    "spec_score": ("validation", "spec_score.json"),
    "completeness": ("validation", "completeness.json"),
    "mermaid": ("artifacts", "mermaid.json"),
    "embedding_status": ("system", "embedding_status.json"),
    "system_spec": ("system_spec.json",),
}

TEXT_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "ddl_sql": ("artifacts", "ddl.sql"),
}

# Regex that only allows safe doc_id values: UUID-like, alphanumerics, hyphens, underscores.
_SAFE_DOC_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,254}$")


class UnsafeDocIdError(ValueError):
    """Raised when a doc_id contains path traversal or unsafe characters."""


def _validate_doc_id(doc_id: str) -> str:
    """Validate *doc_id* is safe for filesystem use; raise on traversal attempts."""
    if not doc_id or not _SAFE_DOC_ID_RE.match(doc_id):
        raise UnsafeDocIdError(
            f"Invalid doc_id {doc_id!r}: must be 1-255 alphanumeric/hyphen/underscore chars"
        )
    # Belt-and-suspenders: reject any path separators or parent references.
    if ".." in doc_id or "/" in doc_id or "\\" in doc_id:
        raise UnsafeDocIdError(f"Invalid doc_id {doc_id!r}: path traversal detected")
    return doc_id


def doc_dir(base_dir: Path, doc_id: str) -> Path:
    """Return the canonical artifact directory for *doc_id*."""
    _validate_doc_id(doc_id)
    resolved = (base_dir / doc_id).resolve()
    # Ensure the resolved path is still inside base_dir.
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise UnsafeDocIdError(f"doc_id {doc_id!r} resolves outside base_dir")
    return resolved


def spec_dir(base_dir: Path, doc_id: str) -> Path:
    """Return the agent spec directory for *doc_id*."""
    _validate_doc_id(doc_id)
    resolved = (base_dir / f"{doc_id}_spec").resolve()
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise UnsafeDocIdError(f"doc_id {doc_id!r}_spec resolves outside base_dir")
    return resolved


def artifact_path(base_dir: Path, doc_id: str, artifact_name: str) -> Path:
    """Return the concrete filesystem path for *artifact_name*."""
    parts = JSON_ARTIFACTS.get(artifact_name) or TEXT_ARTIFACTS.get(artifact_name)
    if parts is None:
        raise KeyError(f"Unknown artifact {artifact_name!r}")
    return doc_dir(base_dir, doc_id).joinpath(*parts)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_artifact_bundle(base_dir: Path, doc_id: str, bundle: dict[str, Any]) -> Path:
    """Persist a standard Spec-OS artifact bundle atomically and return the doc directory.

    Writes to a temporary directory first, then atomically renames it into
    place so that an interrupted write never leaves a partial bundle on disk.
    """
    target = doc_dir(base_dir, doc_id)

    # Write into a temporary staging directory *next to* the target so that
    # os.rename / shutil.move is an atomic same-filesystem operation.
    staging_dir = Path(tempfile.mkdtemp(dir=base_dir, prefix=f".{doc_id}_staging_"))
    try:
        for key, parts in JSON_ARTIFACTS.items():
            if key in bundle:
                _write_json(staging_dir.joinpath(*parts), bundle[key])

        for key, parts in TEXT_ARTIFACTS.items():
            if key in bundle:
                _write_text(staging_dir.joinpath(*parts), bundle[key])

        # Atomic swap: remove any existing bundle, then rename staging → target.
        if target.exists():
            shutil.rmtree(target)
        staging_dir.rename(target)
    except BaseException:
        # Clean up the staging directory on any failure.
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise

    return target


def load_json_artifact(base_dir: Path, doc_id: str, artifact_name: str) -> Any:
    """Load a JSON artifact from disk."""
    path = artifact_path(base_dir, doc_id, artifact_name)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Artifact {artifact_name!r} not found for doc {doc_id!r}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in artifact {artifact_name!r} for doc {doc_id!r}: {exc}") from exc


def load_text_artifact(base_dir: Path, doc_id: str, artifact_name: str) -> str:
    """Load a text artifact from disk."""
    path = artifact_path(base_dir, doc_id, artifact_name)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Artifact {artifact_name!r} not found for doc {doc_id!r}") from exc


def list_document_dirs(base_dir: Path) -> list[Path]:
    """Return document directories that contain a system spec."""
    if not base_dir.exists():
        return []
    docs: list[Path] = []
    for path in sorted(base_dir.iterdir()):
        if path.is_dir() and path.name.endswith("_spec"):
            continue
        if path.is_dir() and path.name.startswith("."):
            continue  # skip staging directories
        if path.is_dir() and path.joinpath(*JSON_ARTIFACTS["system_spec"]).exists():
            docs.append(path)
    return docs


def delete_document_bundle(base_dir: Path, doc_id: str) -> None:
    """Delete the document artifact directory and generated spec folder."""
    target = doc_dir(base_dir, doc_id)
    if target.exists():
        shutil.rmtree(target)

    generated_spec_dir = spec_dir(base_dir, doc_id)
    if generated_spec_dir.exists():
        shutil.rmtree(generated_spec_dir)
