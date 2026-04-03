"""Core parity checks for the remaining shadow-compiler artifact pack."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from spec_os.compiler.emitters import (
    compile_completeness_artifact,
    compile_computation_graph_artifact,
    compile_computation_validation_artifact,
    compile_document_lineage_artifact,
    compile_graph_validation_artifact,
    compile_issue_catalog_artifact,
    compile_reconciliation_artifact,
    compile_review_decisions_artifact,
    compile_roadmap_artifact,
    compile_spec_score_artifact,
    compile_system_spec_artifact,
    compile_traceability_artifact,
)
from spec_os.compiler.specos_repo_loader import load_specos_repo_ir

DEFAULT_SPEC_PACK = Path("/tmp/Modelling_Engine_SpecOS_20260403")


def _spec_pack() -> Path:
    path = Path(os.environ.get("SPECOS_SHADOW_REPO", str(DEFAULT_SPEC_PACK))).expanduser()
    if not path.exists():
        pytest.skip(f"SPECOS_SHADOW_REPO not found: {path}")
    return path


def _without_meta(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key != "meta"}


def test_traceability_roadmap_lineage_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)

    traceability = compile_traceability_artifact(ir)
    roadmap = compile_roadmap_artifact(ir)
    lineage = compile_document_lineage_artifact(ir)

    source_traceability = json.loads((spec_pack / "artifacts" / "traceability.json").read_text(encoding="utf-8"))
    source_roadmap = json.loads((spec_pack / "artifacts" / "roadmap.json").read_text(encoding="utf-8"))
    source_lineage = json.loads((spec_pack / "artifacts" / "document_lineage.json").read_text(encoding="utf-8"))

    assert _without_meta(traceability) == _without_meta(source_traceability)
    assert _without_meta(roadmap) == _without_meta(source_roadmap)
    assert _without_meta(lineage) == _without_meta(source_lineage)


def test_validation_and_system_spec_core_parity():
    spec_pack = _spec_pack()
    ir = load_specos_repo_ir(spec_pack)
    benchmark_doc_count = len(ir.phases["phase_1_foundation_contracts.specos.json"]["meta"]["benchmark_docs"])

    traceability = compile_traceability_artifact(ir)
    computation_graph = compile_computation_graph_artifact(ir)
    graph_validation = compile_graph_validation_artifact(ir, computation_graph)
    computation_validation = compile_computation_validation_artifact(ir, computation_graph)
    completeness = compile_completeness_artifact(ir, ir.inventory.counts, benchmark_doc_count)
    reconciliation = compile_reconciliation_artifact(ir, completeness, computation_graph, benchmark_doc_count)
    issue_catalog = compile_issue_catalog_artifact(ir, completeness, reconciliation)
    review_decisions = compile_review_decisions_artifact(ir)
    spec_score = compile_spec_score_artifact(
        ir,
        completeness,
        reconciliation,
        traceability,
        graph_validation,
        computation_validation,
        issue_catalog,
    )
    system_spec = compile_system_spec_artifact(ir)

    source_graph_validation = json.loads((spec_pack / "validation" / "graph_validation.json").read_text(encoding="utf-8"))
    source_computation_validation = json.loads((spec_pack / "validation" / "computation_validation.json").read_text(encoding="utf-8"))
    source_completeness = json.loads((spec_pack / "validation" / "completeness.json").read_text(encoding="utf-8"))
    source_reconciliation = json.loads((spec_pack / "validation" / "reconciliation.json").read_text(encoding="utf-8"))
    source_issue_catalog = json.loads((spec_pack / "validation" / "issue_catalog.json").read_text(encoding="utf-8"))
    source_review_decisions = json.loads((spec_pack / "validation" / "review_decisions.json").read_text(encoding="utf-8"))
    source_spec_score = json.loads((spec_pack / "validation" / "spec_score.json").read_text(encoding="utf-8"))
    source_system_spec = json.loads((spec_pack / "artifacts" / "system_spec.json").read_text(encoding="utf-8"))

    assert _without_meta(graph_validation) == _without_meta(source_graph_validation)
    assert _without_meta(computation_validation) == _without_meta(source_computation_validation)
    assert _without_meta(completeness) == _without_meta(source_completeness)
    assert _without_meta(reconciliation) == _without_meta(source_reconciliation)
    assert _without_meta(issue_catalog) == _without_meta(source_issue_catalog)
    assert _without_meta(review_decisions) == _without_meta(source_review_decisions)
    assert _without_meta(spec_score) == _without_meta(source_spec_score)
    assert _without_meta(system_spec) == _without_meta(source_system_spec)
