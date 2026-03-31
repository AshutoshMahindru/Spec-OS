"""End-to-end pipeline integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_file
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
