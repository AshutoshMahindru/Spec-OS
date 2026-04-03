"""Shared artifact writer / reader layer."""

from __future__ import annotations

import json
import shutil
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


def doc_dir(base_dir: Path, doc_id: str) -> Path:
    """Return the canonical artifact directory for *doc_id*."""
    return base_dir / doc_id


def spec_dir(base_dir: Path, doc_id: str) -> Path:
    """Return the agent spec directory for *doc_id*."""
    return base_dir / f"{doc_id}_spec"


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
    """Persist a standard Spec-OS artifact bundle and return the doc directory."""
    target = doc_dir(base_dir, doc_id)
    target.mkdir(parents=True, exist_ok=True)

    for key, parts in JSON_ARTIFACTS.items():
        if key in bundle:
            _write_json(target.joinpath(*parts), bundle[key])

    for key, parts in TEXT_ARTIFACTS.items():
        if key in bundle:
            _write_text(target.joinpath(*parts), bundle[key])

    return target


def load_json_artifact(base_dir: Path, doc_id: str, artifact_name: str) -> Any:
    """Load a JSON artifact from disk."""
    path = artifact_path(base_dir, doc_id, artifact_name)
    return json.loads(path.read_text(encoding="utf-8"))


def load_text_artifact(base_dir: Path, doc_id: str, artifact_name: str) -> str:
    """Load a text artifact from disk."""
    path = artifact_path(base_dir, doc_id, artifact_name)
    return path.read_text(encoding="utf-8")


def list_document_dirs(base_dir: Path) -> list[Path]:
    """Return document directories that contain a system spec."""
    if not base_dir.exists():
        return []
    docs: list[Path] = []
    for path in sorted(base_dir.iterdir()):
        if path.is_dir() and path.name.endswith("_spec"):
            continue
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
