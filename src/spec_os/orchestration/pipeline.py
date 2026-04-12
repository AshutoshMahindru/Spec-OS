"""End-to-end ingestion pipeline (V2 -- fully wired)."""

from __future__ import annotations

import logging
import traceback
import uuid
from pathlib import Path
from typing import Any

from spec_os.api.contracts import (
    bind_api_to_schema,
    build_api_contracts_from_canonical,
    build_api_contracts_from_graph,
)
from spec_os.artifacts import (
    EmbeddingStatusModel,
    ExecutionPlanModel,
    ReconciliationModel,
    SystemSpecModel,
    TraceabilityRowModel,
    load_json_artifact,
    write_artifact_bundle,
)
from spec_os.canonical.model import build_canonical_model
from spec_os.compiler import build_modelling_engine_specos_compiler_import
from spec_os.computation.dag import build_computation_graph, build_execution_plan
from spec_os.config import settings
from spec_os.embeddings import embed_chunks, get_embedding_status, store_embeddings
from spec_os.errors import build_error_payload
from spec_os.extraction.classifier import classify_document
from spec_os.extraction.router import route_extraction
from spec_os.importers import build_modelling_engine_specos_import
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


def _debug_block(exc: Exception) -> dict[str, Any] | None:
    if not settings.debug_mode:
        return None
    return {
        "exception_type": type(exc).__name__,
        "trace": traceback.format_exc(),
    }


def _build_system_spec(
    *,
    doc_id: str,
    doc_type: str,
    spec_score: dict,
    completeness: dict,
    canonical_model: dict,
    canonical_schema: dict,
    ddl_sql: str,
    api_contracts: list[dict],
    api_bindings: list[dict],
    computation_graph: dict,
    execution_plan: dict,
    var_table_map: dict,
    reconciliation: dict,
    embedding_status: dict,
    source_documents: list[dict] | None = None,
) -> dict[str, Any]:
    return SystemSpecModel.model_validate(
        {
            "meta": {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "spec_score": spec_score.get("score"),
            "ready_for_codegen": completeness.get("ready_for_codegen"),
            "embedding_backend": embedding_status.get("actual_backend", "none"),
        },
            "sources": source_documents or [],
            "canonical": canonical_model,
            "data_model": {"schema": canonical_schema, "ddl": ddl_sql},
            "application": {"apis": api_contracts, "bindings": api_bindings},
            "computation": {"graph": computation_graph, "execution_plan": execution_plan},
            "runtime": {"variable_mapping": var_table_map, "embeddings": embedding_status},
            "validation": {"reconciliation": reconciliation, "completeness": completeness},
        }
    ).model_dump(mode="json")


def _build_artifact_bundle(
    *,
    structured_payload: dict,
    graph: dict,
    graph_validation: dict,
    canonical_model: dict,
    computation_validation: dict,
    schema: dict,
    roadmap: list[dict],
    traceability: list[dict],
    computation_graph: dict,
    api_contracts: list[dict],
    variable_registry: dict,
    canonical_schema: dict,
    reconciliation: dict,
    var_table_map: dict,
    execution_plan: dict,
    api_bindings: list[dict],
    spec_score: dict,
    completeness: dict,
    mermaid: dict,
    ddl_sql: str,
    embedding_status: dict,
    system_spec: dict,
) -> dict[str, Any]:
    return {
        "structured": structured_payload,
        "graph": graph,
        "graph_validation": graph_validation,
        "canonical_model": canonical_model,
        "computation_validation": computation_validation,
        "schema": schema,
        "roadmap": roadmap,
        "traceability": traceability,
        "computation_graph": computation_graph,
        "api_contracts": api_contracts,
        "variable_registry": variable_registry,
        "canonical_schema": canonical_schema,
        "reconciliation": reconciliation,
        "variable_mapping": var_table_map,
        "execution_plan": execution_plan,
        "api_bindings": api_bindings,
        "spec_score": spec_score,
        "completeness": completeness,
        "mermaid": mermaid,
        "ddl_sql": ddl_sql,
        "embedding_status": embedding_status,
        "system_spec": system_spec,
    }


def ingest_file(file_path: str | Path) -> dict:
    """Run the full V2 pipeline on *file_path* and return a summary dict."""
    settings.ensure_dirs()
    doc_id = str(uuid.uuid4())

    try:
        # ── LAYER 1: Parse ──────────────────────────────────────────────
        html = parse_mhtml(file_path)
        structured = clean_html(html)

        # ── LAYER 1.5: Chunk + Embed ────────────────────────────────────
        chunks = chunk_text(structured, doc_id)
        embedding_status = get_embedding_status(enabled=settings.enable_embeddings, backend=settings.embedding_backend)
        embeddings: list[dict] = []
        if embedding_status["available"]:
            embeddings = embed_chunks(chunks, backend=embedding_status["actual_backend"], dim=settings.embedding_dim)
            embedding_status["stored"] = store_embeddings(
                embeddings,
                vectors_file=settings.vectors_file,
                index_file=settings.faiss_index_file,
                dim=settings.embedding_dim,
            )
        else:
            logger.info("Skipping embeddings for %s (%s)", doc_id, embedding_status.get("reason"))
        embedding_status = EmbeddingStatusModel.model_validate(embedding_status).model_dump(mode="json")

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
        var_table_map = build_variable_to_table_mapping(schema, variable_registry, computation_graph)
        execution_plan = ExecutionPlanModel.model_validate(build_execution_plan(computation_graph)).model_dump(mode="json")
        api_bindings = bind_api_to_schema(api_contracts, schema)

        # ── LAYER 5: Validation (foolproof reconciliation) ──────────────
        comp_validation = validate_computation_graph(computation_graph)
        reconciliation = ReconciliationModel.model_validate(
            reconcile_spec(
                graph, schema, variable_registry, api_contracts,
                canonical_model=canonical_model,
                computation_validation=comp_validation,
                graph_validation=graph_validation,
            )
        ).model_dump(mode="json")
        spec_score = compute_spec_quality_score(
            reconciliation, variable_registry, schema, api_contracts, computation_graph,
            doc_type=doc_type,
        )
        completeness = build_spec_completeness(
            reconciliation, variable_registry, schema, api_contracts, computation_graph,
            doc_type=doc_type,
        )

        # ── LAYER 6: Visualisation + outputs ────────────────────────────
        mermaid = generate_mermaid_diagrams(graph, computation_graph)
        ddl_sql = generate_starter_ddl(graph, schema=schema, doc_type=doc_type)
        roadmap = build_engineering_roadmap(graph, doc_type)
        traceability = [
            row.model_dump(mode="json")
            for row in (
                TraceabilityRowModel.model_validate(item) for item in build_traceability_matrix(structured, graph, doc_type)
            )
        ]

        system_spec = _build_system_spec(
            doc_id=doc_id,
            doc_type=doc_type,
            spec_score=spec_score,
            completeness=completeness,
            canonical_model=canonical_model,
            canonical_schema=canonical_schema,
            ddl_sql=ddl_sql,
            api_contracts=api_contracts,
            api_bindings=api_bindings,
            computation_graph=computation_graph,
            execution_plan=execution_plan,
            var_table_map=var_table_map,
            reconciliation=reconciliation,
            embedding_status=embedding_status,
            source_documents=[{"source": Path(file_path).name, "doc_type": doc_type}],
        )
        write_artifact_bundle(
            settings.base_dir,
            doc_id,
            _build_artifact_bundle(
                structured_payload={"structured": structured, "chunks": chunks, "source": Path(file_path).name},
                graph=graph,
                graph_validation=graph_validation,
                canonical_model=canonical_model,
                computation_validation=comp_validation,
                schema=schema,
                roadmap=roadmap,
                traceability=traceability,
                computation_graph=computation_graph,
                api_contracts=api_contracts,
                variable_registry=variable_registry,
                canonical_schema=canonical_schema,
                reconciliation=reconciliation,
                var_table_map=var_table_map,
                execution_plan=execution_plan,
                api_bindings=api_bindings,
                spec_score=spec_score,
                completeness=completeness,
                mermaid=mermaid,
                ddl_sql=ddl_sql,
                embedding_status=embedding_status,
                system_spec=system_spec,
            ),
        )

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
            "embedding_backend": embedding_status.get("actual_backend", "none"),
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
        return build_error_payload(
            doc_id=doc_id,
            error_code="INGESTION_FAILED",
            message="Failed to ingest file",
            details={"source": str(file_path)},
            debug=_debug_block(exc),
        )


def ingest_specos_repo(repo_path: str | Path, doc_id: str | None = None, mode: str = "importer") -> dict:
    """Import or compile a Modelling_Engine_SpecOS repo into a standard Spec-OS bundle."""
    settings.ensure_dirs()

    try:
        if mode == "importer":
            imported = build_modelling_engine_specos_import(repo_path, doc_id=doc_id)
            status = "imported"
            import_mode = "modelling_engine_specos"
        elif mode == "compiler":
            imported = build_modelling_engine_specos_compiler_import(repo_path, doc_id=doc_id)
            status = "compiled"
            import_mode = "modelling_engine_specos_compiler"
        else:
            raise ValueError(f"Unsupported spec repo mode: {mode}")

        write_artifact_bundle(settings.base_dir, imported["doc_id"], imported["bundle"])
        spec_dir = generate_spec_folder(
            settings.base_dir,
            imported["doc_id"],
            imported["spec_folder_payload"],
        )
        return {
            "doc_id": imported["doc_id"],
            "spec_dir": str(spec_dir),
            "doc_type": imported["doc_type"],
            "embedding_backend": imported["bundle"]["embedding_status"].get("actual_backend", "none"),
            "status": status,
            "import_mode": import_mode,
            **({"compiler_mode": imported["compiler_mode"]} if "compiler_mode" in imported else {}),
            **imported["counts"],
        }
    except Exception as exc:
        logger.exception("Spec repo %s failed for %s", mode, repo_path)
        return build_error_payload(
            doc_id=doc_id,
            error_code="SPECOS_COMPILER_FAILED" if mode == "compiler" else "SPECOS_IMPORT_FAILED",
            message=(
                "Failed to compile Modelling_Engine_SpecOS repo"
                if mode == "compiler"
                else "Failed to import Modelling_Engine_SpecOS repo"
            ),
            details={"source": str(repo_path), "mode": mode},
            debug=_debug_block(exc),
        )


def ingest_multiple_files(file_paths: list[str]) -> dict:
    """Ingest several files and merge into a unified spec."""
    from spec_os.merge import merge_all_docs

    results: list[dict] = []
    failures: list[dict] = []
    for fp in file_paths:
        res = ingest_file(fp)
        if res.get("status") != "processed":
            failures.append({"source": fp, "error": res})
            continue
        doc_id = res["doc_id"]
        results.append(
            {
                "graph": load_json_artifact(settings.base_dir, doc_id, "graph"),
                "schema": load_json_artifact(settings.base_dir, doc_id, "schema"),
                "variable_registry": load_json_artifact(settings.base_dir, doc_id, "variable_registry"),
                "traceability": load_json_artifact(settings.base_dir, doc_id, "traceability"),
                "structured": load_json_artifact(settings.base_dir, doc_id, "structured"),
                "system_spec": load_json_artifact(settings.base_dir, doc_id, "system_spec"),
            }
        )

    if not results:
        return build_error_payload(
            doc_id=None,
            error_code="NO_VALID_DOCS",
            message="No valid documents were processed",
            details={"failed_docs": failures},
        )

    merged = merge_all_docs(results)
    merged_id = str(uuid.uuid4())
    source_documents = [doc["system_spec"].get("meta", {}) for doc in results]
    graph_validation = validate_graph(merged["graph"])
    comp_validation = validate_computation_graph(merged["computation_graph"])
    canonical_model = build_canonical_model(merged["graph"])
    variable_registry = merged["variable_registry"]
    schema = merged["schema"]
    canonical_schema = build_canonical_schema(schema, variable_registry)
    var_table_map = build_variable_to_table_mapping(schema, variable_registry, merged["computation_graph"])
    api_bindings = bind_api_to_schema(merged["api_contracts"], schema)
    spec_score = compute_spec_quality_score(
        merged["reconciliation"],
        variable_registry,
        schema,
        merged["api_contracts"],
        merged["computation_graph"],
        doc_type="MERGED",
    )
    completeness = build_spec_completeness(
        merged["reconciliation"],
        variable_registry,
        schema,
        merged["api_contracts"],
        merged["computation_graph"],
        doc_type="MERGED",
    )
    mermaid = generate_mermaid_diagrams(merged["graph"], merged["computation_graph"])
    ddl_sql = generate_starter_ddl(merged["graph"], schema=schema, doc_type="MERGED")
    roadmap = build_engineering_roadmap(merged["graph"], "MERGED")
    traceability = [
        row.model_dump(mode="json")
        for row in (
            TraceabilityRowModel.model_validate(item) for doc in results for item in doc.get("traceability", [])
        )
    ]
    embedding_status = EmbeddingStatusModel.model_validate(
        {
        "enabled": False,
        "requested_backend": settings.embedding_backend,
        "actual_backend": "none",
        "available": False,
        "stored": False,
        "reason": "merge_output",
        }
    ).model_dump(mode="json")
    merged["execution_plan"] = ExecutionPlanModel.model_validate(merged["execution_plan"]).model_dump(mode="json")
    merged["reconciliation"] = ReconciliationModel.model_validate(merged["reconciliation"]).model_dump(mode="json")
    system_spec = _build_system_spec(
        doc_id=merged_id,
        doc_type="MERGED",
        spec_score=spec_score,
        completeness=completeness,
        canonical_model=canonical_model,
        canonical_schema=canonical_schema,
        ddl_sql=ddl_sql,
        api_contracts=merged["api_contracts"],
        api_bindings=api_bindings,
        computation_graph=merged["computation_graph"],
        execution_plan=merged["execution_plan"],
        var_table_map=var_table_map,
        reconciliation=merged["reconciliation"],
        embedding_status=embedding_status,
        source_documents=source_documents,
    )
    write_artifact_bundle(
        settings.base_dir,
        merged_id,
        _build_artifact_bundle(
            structured_payload={
                "structured": [],
                "chunks": [],
                "source_documents": source_documents,
                "merge_mode": "multi_document",
            },
            graph=merged["graph"],
            graph_validation=graph_validation,
            canonical_model=canonical_model,
            computation_validation=comp_validation,
            schema=schema,
            roadmap=roadmap,
            traceability=traceability,
            computation_graph=merged["computation_graph"],
            api_contracts=merged["api_contracts"],
            variable_registry=variable_registry,
            canonical_schema=canonical_schema,
            reconciliation=merged["reconciliation"],
            var_table_map=var_table_map,
            execution_plan=merged["execution_plan"],
            api_bindings=api_bindings,
            spec_score=spec_score,
            completeness=completeness,
            mermaid=mermaid,
            ddl_sql=ddl_sql,
            embedding_status=embedding_status,
            system_spec=system_spec,
        ),
    )

    spec_dir = generate_spec_folder(
        settings.base_dir,
        merged_id,
        {
            "schema": canonical_schema,
            "api_contracts": merged["api_contracts"],
            "computation_graph": merged["computation_graph"],
            "execution_plan": merged["execution_plan"],
        },
    )

    return {
        "merged_id": merged_id,
        "doc_id": merged_id,
        "spec_dir": str(spec_dir),
        "status": "merged",
        "processed_docs": len(results),
        "failed_docs": failures,
    }
