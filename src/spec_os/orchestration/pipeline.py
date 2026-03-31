"""End-to-end ingestion pipeline (V2 -- fully wired)."""

from __future__ import annotations

import json
import logging
import os
import traceback
import uuid
from pathlib import Path

from spec_os.api.contracts import (
    bind_api_to_schema,
    build_api_contracts_from_canonical,
    build_api_contracts_from_graph,
)
from spec_os.canonical.model import build_canonical_model
from spec_os.computation.dag import build_computation_graph, build_execution_plan
from spec_os.config import settings
from spec_os.embeddings import embed_chunks, store_embeddings
from spec_os.extraction.classifier import classify_document
from spec_os.extraction.router import route_extraction
from spec_os.orchestration.artifacts import build_engineering_roadmap, build_traceability_matrix
from spec_os.orchestration.spec_folder import generate_spec_folder
from spec_os.parsing.chunker import chunk_text
from spec_os.parsing.html_cleaner import clean_html
from spec_os.parsing.mhtml import parse_mhtml
from spec_os.schema.builder import build_canonical_schema, build_data_schema_from_canonical
from spec_os.schema.ddl import generate_starter_ddl
from spec_os.schema.enrichment import enrich_schema_types
from spec_os.validation.completeness import build_spec_completeness, compute_spec_quality_score
from spec_os.validation.graph_validator import validate_computation_graph, validate_graph
from spec_os.validation.reconciliation import build_variable_to_table_mapping, reconcile_spec
from spec_os.visualization import generate_mermaid_diagrams

logger = logging.getLogger(__name__)


def _save_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def ingest_file(file_path: str | Path) -> dict:
    """Run the full V2 pipeline on *file_path* and return a summary dict."""
    settings.ensure_dirs()
    doc_id = str(uuid.uuid4())
    doc_dir = settings.base_dir / doc_id

    def p(*parts: str) -> Path:
        path = doc_dir.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    try:
        # ── LAYER 1: Parse ──────────────────────────────────────────────
        html = parse_mhtml(file_path)
        structured = clean_html(html)

        # ── LAYER 1.5: Chunk + Embed ────────────────────────────────────
        chunks = chunk_text(structured, doc_id)
        embeddings = embed_chunks(chunks)
        store_embeddings(
            embeddings,
            vectors_file=settings.vectors_file,
            index_file=settings.faiss_index_file,
        )

        # ── LAYER 2: Extraction ─────────────────────────────────────────
        doc_type = classify_document(structured)
        graph = route_extraction(structured, doc_id, doc_type)
        graph_validation = validate_graph(graph)

        for node in graph["nodes"]:
            if node["type"] == "Document":
                node["doc_type"] = doc_type
                node["source"] = Path(file_path).name
                break

        # ── LAYER 3: Canonical model (source of truth) ──────────────────
        canonical_model = build_canonical_model(graph)
        variable_registry = {"variables": canonical_model.get("variables", [])}

        # ── LAYER 4: Domain models (all from canonical) ─────────────────
        schema = build_data_schema_from_canonical(canonical_model)
        schema = enrich_schema_types(schema)
        computation_graph = build_computation_graph(canonical_model)

        # BUG-FIX: use the canonical-aware builder, then fall back to graph
        api_contracts = build_api_contracts_from_canonical(canonical_model)
        if not api_contracts:
            api_contracts = build_api_contracts_from_graph(graph)

        canonical_schema = build_canonical_schema(schema, variable_registry)
        var_table_map = build_variable_to_table_mapping(schema, variable_registry)
        execution_plan = build_execution_plan(computation_graph)
        api_bindings = bind_api_to_schema(api_contracts, schema)

        # ── LAYER 5: Validation ─────────────────────────────────────────
        comp_validation = validate_computation_graph(computation_graph)
        reconciliation = reconcile_spec(graph, schema, variable_registry, api_contracts)
        spec_score = compute_spec_quality_score(reconciliation, variable_registry, schema, api_contracts, computation_graph)
        completeness = build_spec_completeness(reconciliation, variable_registry, schema, api_contracts, computation_graph)

        # ── LAYER 6: Visualisation + outputs ────────────────────────────
        mermaid = generate_mermaid_diagrams(graph, computation_graph)
        ddl_sql = generate_starter_ddl(graph, schema=schema, doc_type=doc_type)
        roadmap = build_engineering_roadmap(graph, doc_type)
        traceability = build_traceability_matrix(structured, graph, doc_type)

        # ── Save artifacts ──────────────────────────────────────────────
        _save_json(p("layers", "structured.json"), {"structured": structured, "chunks": chunks})
        _save_json(p("layers", "graph.json"), graph)
        _save_json(p("validation", "graph_validation.json"), graph_validation)
        _save_json(p("canonical", "canonical_model.json"), canonical_model)
        _save_json(p("validation", "computation_validation.json"), comp_validation)
        _save_json(p("domain", "schema.json"), schema)
        _save_json(p("artifacts", "roadmap.json"), roadmap)
        _save_json(p("artifacts", "traceability.json"), traceability)
        _save_json(p("domain", "computation_graph.json"), computation_graph)
        _save_json(p("domain", "api_contracts.json"), api_contracts)
        _save_json(p("canonical", "variable_registry.json"), variable_registry)
        _save_json(p("domain", "canonical_schema.json"), canonical_schema)
        _save_json(p("validation", "reconciliation.json"), reconciliation)
        _save_json(p("system", "variable_mapping.json"), var_table_map)
        _save_json(p("system", "execution_plan.json"), execution_plan)
        _save_json(p("system", "api_bindings.json"), api_bindings)
        _save_json(p("validation", "spec_score.json"), spec_score)
        _save_json(p("validation", "completeness.json"), completeness)
        _save_json(p("artifacts", "mermaid.json"), mermaid)
        p("artifacts", "ddl.sql").write_text(ddl_sql, encoding="utf-8")

        # -- System spec
        system_spec = {
            "meta": {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "spec_score": spec_score.get("score"),
                "ready_for_codegen": completeness.get("ready_for_codegen"),
            },
            "canonical": canonical_model,
            "data_model": {"schema": canonical_schema, "ddl": ddl_sql},
            "application": {"apis": api_contracts, "bindings": api_bindings},
            "computation": {"graph": computation_graph, "execution_plan": execution_plan},
            "runtime": {"variable_mapping": var_table_map},
            "validation": {"reconciliation": reconciliation, "completeness": completeness},
        }
        _save_json(p("system_spec.json"), system_spec)

        # -- Spec folder
        spec_dir = generate_spec_folder(
            settings.base_dir,
            doc_id,
            {
                "schema": canonical_schema,
                "api_contracts": api_contracts,
                "computation_graph": computation_graph,
                "execution_plan": execution_plan,
            },
        )

        return {
            "doc_id": doc_id,
            "spec_dir": str(spec_dir),
            "chunks": len(chunks),
            "doc_type": doc_type,
            "graph_nodes": len(graph["nodes"]),
            "graph_edges": len(graph["edges"]),
            "schema_models": len(schema.get("models", [])),
            "schema_apis": len(schema.get("apis", [])),
            "traceability_rows": len(traceability),
            "metrics": len(computation_graph.get("metrics", [])),
            "apis": len(api_contracts),
            "variables": len(variable_registry.get("variables", [])),
            "reconciliation_issues": len(reconciliation.get("issues", [])),
            "spec_score": spec_score.get("score"),
            "ready_for_codegen": completeness.get("ready_for_codegen"),
            "status": "processed",
        }

    except Exception as exc:
        logger.exception("Ingestion failed for %s", file_path)
        return {
            "doc_id": doc_id,
            "status": "error",
            "error": str(exc),
            "trace": traceback.format_exc(),
        }


def ingest_multiple_files(file_paths: list[str]) -> dict:
    """Ingest several files and merge into a unified spec."""
    from spec_os.merge import merge_all_docs

    results: list[dict] = []
    for fp in file_paths:
        res = ingest_file(fp)
        if res.get("status") != "processed":
            continue
        doc_id = res["doc_id"]
        base = settings.base_dir / doc_id

        with (base / "layers" / "graph.json").open() as f:
            graph = json.load(f)
        with (base / "domain" / "schema.json").open() as f:
            schema = json.load(f)
        with (base / "canonical" / "variable_registry.json").open() as f:
            registry = json.load(f)

        results.append({"graph": graph, "schema": schema, "variable_registry": registry})

    if not results:
        return {"status": "error", "message": "No valid docs processed"}

    merged = merge_all_docs(results)
    merged_id = str(uuid.uuid4())
    merged_dir = settings.base_dir / merged_id
    merged_dir.mkdir(parents=True, exist_ok=True)

    _save_json(merged_dir / "graph.json", merged["graph"])
    _save_json(merged_dir / "schema.json", merged["schema"])
    _save_json(merged_dir / "variable_registry.json", merged["variable_registry"])
    _save_json(merged_dir / "execution_plan.json", merged["execution_plan"])

    spec_dir = generate_spec_folder(
        settings.base_dir,
        merged_id,
        {
            "schema": merged["schema"],
            "api_contracts": merged["api_contracts"],
            "computation_graph": merged["computation_graph"],
            "execution_plan": merged["execution_plan"],
        },
    )

    return {"merged_id": merged_id, "spec_dir": str(spec_dir), "status": "merged"}
