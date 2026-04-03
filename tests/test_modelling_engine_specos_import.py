"""Tests for importing a Modelling_Engine_SpecOS artifact pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from spec_os import cli
from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_specos_repo


@pytest.fixture(autouse=True)
def use_tmp_data_dir(tmp_path):
    original_base_dir = settings.base_dir
    settings.base_dir = tmp_path / "data"
    settings.ensure_dirs()
    yield
    settings.base_dir = original_base_dir


@pytest.fixture
def modelling_engine_specos_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "Modelling_Engine_SpecOS"
    files = {
        "artifacts/spec_os_import_manifest.json": {
            "meta": {"version": "1.0", "consumer": "Spec-OS", "import_strategy": "artifact_pack"},
            "recommended_doc_id": "modelling_engine_specos_rc",
            "phase_specs": [
                "specos/phase_1_foundation_contracts.specos.json",
                "specos/phase_2_planning_spine_inputs.specos.json",
            ],
            "json_artifacts": {
                "canonical_model": "artifacts/canonical_model.json",
                "canonical_schema": "artifacts/canonical_schema.json",
                "schema": "artifacts/schema.json",
                "api_contracts": "artifacts/api_contracts.json",
                "computation_graph": "artifacts/computation_graph.json",
                "variable_registry": "artifacts/variable_registry.json",
                "variable_mapping": "artifacts/variable_mapping.json",
                "traceability": "artifacts/traceability.json",
                "roadmap": "artifacts/roadmap.json",
                "document_lineage": "artifacts/document_lineage.json",
                "system_spec": "artifacts/system_spec.json",
                "graph_validation": "validation/graph_validation.json",
                "computation_validation": "validation/computation_validation.json",
                "completeness": "validation/completeness.json",
                "reconciliation": "validation/reconciliation.json",
                "issue_catalog": "validation/issue_catalog.json",
                "review_decisions": "validation/review_decisions.json",
                "spec_score": "validation/spec_score.json",
            },
            "text_artifacts": {"ddl_sql": "artifacts/ddl.sql"},
        },
        "artifacts/canonical_model.json": {
            "canonical_stage_model": [{"order": 1, "stage": "Context", "family": "R-CTX"}],
            "requirement_families": [{"code": "R-CTX", "name": "Context requirements"}],
            "shared_planning_context": {
                "required_fields": [{"name": "companyId", "type": "uuid"}],
                "route_fields": ["companySlug"],
            },
            "governance_state_machine": {"states": ["draft", "approved"]},
            "api_namespace_model": {"namespaces": ["/api/v1/context"]},
        },
        "artifacts/canonical_schema.json": {
            "entities": [
                {
                    "entity_name": "planning_versions",
                    "phase_number": 2,
                    "requirement_families": ["R-CTX"],
                    "fields": ["id", "company_id", "version_label"],
                },
                {
                    "entity_name": "compute_runs",
                    "phase_number": 3,
                    "requirement_families": ["R-CMP"],
                    "fields": ["id", "scenario_id", "status"],
                },
            ]
        },
        "artifacts/schema.json": {
            "planning_context": {
                "required_fields": [{"name": "companyId", "type": "uuid"}],
                "route_fields": ["companySlug"],
            },
            "entities": [
                {
                    "entity_name": "planning_versions",
                    "phase_number": 2,
                    "requirement_families": ["R-CTX"],
                    "fields": ["id", "company_id", "version_label"],
                },
                {
                    "entity_name": "compute_runs",
                    "phase_number": 3,
                    "requirement_families": ["R-CMP"],
                    "fields": ["id", "scenario_id", "status"],
                },
            ],
        },
        "artifacts/api_contracts.json": {
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/v1/context/versions",
                    "domain_family": "context",
                    "phase_number": 2,
                    "requirement_families": ["R-CTX"],
                    "owner_doc": "WORKSPACE_FLOW.md",
                },
                {
                    "method": "POST",
                    "path": "/api/v1/compute/runs",
                    "domain_family": "compute",
                    "phase_number": 3,
                    "requirement_families": ["R-CMP"],
                    "owner_doc": "FEATURE_INDEX.md",
                },
            ]
        },
        "artifacts/computation_graph.json": {
            "graph": {
                "nodes": ["node_inputs", "node_revenue"],
                "edges": [["node_inputs", "node_revenue"]],
            },
            "execution_plan": ["resolve_context", "compute_revenue"],
            "freshness_rule": "Invalidate on assumption change.",
        },
        "artifacts/variable_registry.json": {
            "variables": [
                {"name": "demand", "class": "driver", "mapped_table": "assumption_field_bindings"},
                {"name": "price", "class": "driver", "mapped_table": "assumption_field_bindings"},
            ],
            "metrics": [
                {
                    "id": "met_revenue",
                    "formula": "demand * price",
                    "phase_number": 4,
                    "requirement_families": ["R-FIN"],
                    "owner_doc": "FINANCIAL_MODEL.md",
                }
            ],
        },
        "artifacts/variable_mapping.json": {
            "mappings": [
                {
                    "variable_name": "demand",
                    "mapped_table": "assumption_field_bindings",
                    "source_phase": 3,
                    "related_metrics": ["met_revenue"],
                },
                {
                    "variable_name": "price",
                    "mapped_table": "assumption_field_bindings",
                    "source_phase": 3,
                    "related_metrics": ["met_revenue"],
                },
            ]
        },
        "artifacts/traceability.json": {
            "apis": [
                {
                    "artifactType": "api",
                    "artifactName": "/api/v1/context/versions",
                    "ownerDoc": "WORKSPACE_FLOW.md",
                    "citations": ["phase_2"],
                }
            ],
            "routes": [],
            "entities": [
                {
                    "artifactType": "entity",
                    "artifactName": "planning_versions",
                    "ownerDoc": "SCHEMA_OVERVIEW.md",
                    "citations": ["phase_2"],
                }
            ],
            "metrics": [
                {
                    "artifactType": "metric",
                    "artifactName": "met_revenue",
                    "ownerDoc": "FINANCIAL_MODEL.md",
                    "citations": ["phase_4"],
                }
            ],
            "screens": [],
        },
        "artifacts/roadmap.json": {
            "waves": [{"wave": 1, "goal": "Context first", "status": "in_progress", "priority": "P0"}]
        },
        "artifacts/document_lineage.json": {
            "benchmark_docs": ["WORKSPACE_FLOW.md", "FINANCIAL_MODEL.md"],
            "artifacts": [],
        },
        "artifacts/system_spec.json": {"meta": {"status": "release_candidate"}},
        "validation/graph_validation.json": {
            "overall_status": "pass",
            "issues": [],
            "node_count": 2,
            "edge_count": 1,
        },
        "validation/computation_validation.json": {
            "overall_status": "pass",
            "checks": [{"check": "execution_plan_completeness", "status": "pass"}],
        },
        "validation/completeness.json": {
            "authoritative_counts": {"apis": 2, "schema_entities": 2, "metrics": 1, "variables": 2, "screens": 0},
            "actual_counts": {"apis": 2, "schema_entities": 2, "metrics": 1, "variables": 2, "screens": 0, "routes": 0},
            "deltas": {"apis": 0, "schema_entities": 0, "metrics": 0, "variables": 0, "screens": 0},
            "notes": [],
        },
        "validation/reconciliation.json": {
            "checks": [{"check": "artifact_manifest_files_generated", "status": "pass"}],
            "overall_status": "pass",
        },
        "validation/issue_catalog.json": {
            "blocking_issues": 0,
            "issues": [{"id": "COMPLETENESS_READY", "severity": "info", "category": "completeness", "message": "Ready"}],
        },
        "validation/review_decisions.json": {"status": "accepted"},
        "validation/spec_score.json": {
            "meta": {"status": "release_candidate", "content_hash": "abc123def456"},
            "blocking_issues": 0,
            "warnings": 0,
            "ready_for_codegen": True,
            "overall_score": 0.91,
        },
        "artifacts/ddl.sql": "CREATE TABLE planning_versions (id uuid);",
    }

    for relative_path, payload in files.items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative_path.endswith(".sql"):
            target.write_text(str(payload), encoding="utf-8")
        else:
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return repo_root


def test_import_specos_repo_builds_standard_bundle(modelling_engine_specos_repo: Path):
    result = ingest_specos_repo(str(modelling_engine_specos_repo))

    assert result["status"] == "imported"
    assert result["doc_type"] == "SPECOS_REPO"
    assert result["ready_for_codegen"] is True
    assert result["apis"] == 2
    assert result["variables"] == 2

    doc_dir = settings.base_dir / result["doc_id"]
    system_spec = json.loads((doc_dir / "system_spec.json").read_text())
    assert (doc_dir / "domain" / "api_contracts.json").exists()
    assert (doc_dir / "validation" / "spec_score.json").exists()
    assert system_spec["meta"]["spec_score"] == 91.0
    assert system_spec["validation"]["source_validation"]["spec_score"]["ready_for_codegen"] is True
    assert (Path(result["spec_dir"]) / "execution_plan.json").exists()


def test_cli_imports_specos_repo(modelling_engine_specos_repo: Path, tmp_path: Path):
    data_dir = tmp_path / "cli-data"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "spec_os.cli",
            "--specos-repo",
            str(modelling_engine_specos_repo),
            "--data-dir",
            str(data_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["status"] == "imported"
    assert payload["doc_type"] == "SPECOS_REPO"
    assert payload["doc_id"].startswith("modelling_engine_specos_rc_abc123de")
    assert (data_dir / payload["doc_id"] / "system_spec.json").exists()


def test_ingest_specos_repo_compiler_mode_writes_bundle(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "compiler-repo"
    repo_root.mkdir()

    fake_result = {
        "doc_id": "compiled_doc",
        "doc_type": "SPECOS_REPO",
        "bundle": {
            "embedding_status": {"actual_backend": "none"},
            "system_spec": {"meta": {"doc_id": "compiled_doc"}},
            "canonical_schema": {"entities": []},
            "api_contracts": [],
            "computation_graph": {"metrics": [], "graph": {"nodes": [], "edges": []}, "execution_plan": []},
            "execution_plan": {"execution_steps": [], "issues": [], "status": "ok"},
        },
        "spec_folder_payload": {
            "schema": {"entities": []},
            "api_contracts": [],
            "computation_graph": {"metrics": [], "graph": {"nodes": [], "edges": []}, "execution_plan": []},
            "execution_plan": {"execution_steps": [], "issues": [], "status": "ok"},
        },
        "counts": {
            "graph_nodes": 0,
            "graph_edges": 0,
            "schema_models": 0,
            "schema_apis": 0,
            "traceability_rows": 0,
            "metrics": 0,
            "apis": 0,
            "variables": 0,
            "reconciliation_issues": 0,
            "spec_score": 82.34,
            "ready_for_codegen": False,
        },
        "compiler_mode": "shadow_phase_spec_compiler",
    }

    def fake_builder(repo_path: str | Path, doc_id: str | None = None) -> dict:
        assert Path(repo_path) == repo_root
        assert doc_id == "manual_id"
        return fake_result

    monkeypatch.setattr(
        "spec_os.orchestration.pipeline.build_modelling_engine_specos_compiler_import",
        fake_builder,
    )

    result = ingest_specos_repo(str(repo_root), doc_id="manual_id", mode="compiler")

    assert result["status"] == "compiled"
    assert result["import_mode"] == "modelling_engine_specos_compiler"
    assert result["compiler_mode"] == "shadow_phase_spec_compiler"
    assert (settings.base_dir / "compiled_doc" / "system_spec.json").exists()
    assert (Path(result["spec_dir"]) / "execution_plan.json").exists()


def test_cli_compiles_specos_repo_when_mode_is_compiler(monkeypatch, tmp_path: Path, capsys):
    repo_root = tmp_path / "compiler-cli-repo"
    repo_root.mkdir()
    data_dir = tmp_path / "cli-data"

    def fake_ingest(repo_path: str, doc_id: str | None = None, mode: str = "importer") -> dict:
        assert Path(repo_path) == repo_root
        assert doc_id is None
        assert mode == "compiler"
        return {
            "doc_id": "compiled_doc",
            "doc_type": "SPECOS_REPO",
            "status": "compiled",
            "import_mode": "modelling_engine_specos_compiler",
            "compiler_mode": "shadow_phase_spec_compiler",
            "spec_dir": str(data_dir / "compiled_doc_spec"),
            "embedding_backend": "none",
            "graph_nodes": 7,
            "graph_edges": 6,
            "schema_models": 48,
            "schema_apis": 71,
            "traceability_rows": 164,
            "metrics": 12,
            "apis": 71,
            "variables": 6,
            "reconciliation_issues": 5,
            "spec_score": 82.34,
            "ready_for_codegen": False,
        }

    monkeypatch.setattr("spec_os.orchestration.pipeline.ingest_specos_repo", fake_ingest)

    cli.main(
        [
            "--specos-repo",
            str(repo_root),
            "--specos-repo-mode",
            "compiler",
            "--data-dir",
            str(data_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "compiled"
    assert payload["import_mode"] == "modelling_engine_specos_compiler"
    assert payload["compiler_mode"] == "shadow_phase_spec_compiler"
