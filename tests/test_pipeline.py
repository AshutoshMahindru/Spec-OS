"""End-to-end pipeline integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_file, ingest_multiple_files
from spec_os.orchestration.sample import make_sample_mhtml


@pytest.fixture
def sample_mhtml(tmp_path):
    path = tmp_path / "sample.mhtml"
    make_sample_mhtml(path)
    return path


@pytest.fixture(autouse=True)
def use_tmp_data_dir(tmp_path):
    """Redirect output to tmp_path so tests don't pollute the repo."""
    original = settings.base_dir
    settings.base_dir = tmp_path / "data"
    settings.ensure_dirs()
    yield
    settings.base_dir = original


class TestIngestFile:
    def test_successful_ingestion(self, sample_mhtml):
        result = ingest_file(str(sample_mhtml))
        assert result["status"] == "processed"
        assert result["graph_nodes"] > 0
        assert result["traceability_rows"] > 0
        assert result["doc_type"] == "PRD"
        assert result["spec_score"] is not None

    def test_artifacts_written(self, sample_mhtml):
        result = ingest_file(str(sample_mhtml))
        doc_dir = settings.base_dir / result["doc_id"]
        assert (doc_dir / "layers" / "graph.json").exists()
        assert (doc_dir / "canonical" / "canonical_model.json").exists()
        assert (doc_dir / "domain" / "schema.json").exists()
        assert (doc_dir / "artifacts" / "ddl.sql").exists()
        assert (doc_dir / "system_spec.json").exists()

    def test_spec_folder_created(self, sample_mhtml):
        result = ingest_file(str(sample_mhtml))
        spec_dir = Path(result["spec_dir"])
        assert spec_dir.exists()
        assert (spec_dir / "AGENTS.md").exists()
        assert (spec_dir / "canonical_schema.json").exists()

    def test_system_spec_structure(self, sample_mhtml):
        result = ingest_file(str(sample_mhtml))
        doc_dir = settings.base_dir / result["doc_id"]
        spec = json.loads((doc_dir / "system_spec.json").read_text())
        assert "meta" in spec
        assert "canonical" in spec
        assert "data_model" in spec
        assert "computation" in spec
        assert "validation" in spec

    def test_nonexistent_file_returns_error(self):
        result = ingest_file("/nonexistent/file.mhtml")
        assert result["status"] == "error"
        assert result["error_code"] == "INGESTION_FAILED"
        assert "trace" not in result

    def test_production_error_payload_hides_debug_trace(self):
        original_environment = settings.environment
        original_debug_errors = settings.debug_errors
        settings.environment = "production"
        settings.debug_errors = False
        try:
            result = ingest_file("/nonexistent/file.mhtml")
        finally:
            settings.environment = original_environment
            settings.debug_errors = original_debug_errors
        assert result["status"] == "error"
        assert "debug" not in result

    def test_embeddings_are_skipped_when_disabled(self, sample_mhtml):
        original_enabled = settings.enable_embeddings
        original_backend = settings.embedding_backend
        settings.enable_embeddings = False
        settings.embedding_backend = "sentence_transformers"
        try:
            result = ingest_file(str(sample_mhtml))
        finally:
            settings.enable_embeddings = original_enabled
            settings.embedding_backend = original_backend

        doc_dir = settings.base_dir / result["doc_id"]
        embedding_status = json.loads((doc_dir / "system" / "embedding_status.json").read_text())
        assert embedding_status["actual_backend"] == "none"
        assert embedding_status["reason"] == "disabled"


class TestIngestMultipleFiles:
    def test_merge_outputs_standard_artifact_contract(self, tmp_path):
        path_a = make_sample_mhtml(tmp_path / "sample_a.mhtml")
        path_b = make_sample_mhtml(tmp_path / "sample_b.mhtml")

        result = ingest_multiple_files([str(path_a), str(path_b)])

        assert result["status"] == "merged"
        doc_dir = settings.base_dir / result["merged_id"]
        assert (doc_dir / "layers" / "graph.json").exists()
        assert (doc_dir / "canonical" / "canonical_model.json").exists()
        assert (doc_dir / "domain" / "schema.json").exists()
        assert (doc_dir / "validation" / "reconciliation.json").exists()
        assert (doc_dir / "system" / "execution_plan.json").exists()
        assert (doc_dir / "system_spec.json").exists()

    def test_merge_reports_partial_failures(self, sample_mhtml):
        result = ingest_multiple_files([str(sample_mhtml), "/nonexistent/file.mhtml"])

        assert result["status"] == "merged"
        assert result["processed_docs"] == 1
        assert len(result["failed_docs"]) == 1
