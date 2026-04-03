"""Tests for typed artifact payload models."""

from __future__ import annotations

import json

from spec_os.artifacts import EmbeddingStatusModel, ExecutionPlanModel, ReconciliationModel, SystemSpecModel
from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_file
from spec_os.orchestration.sample import make_sample_mhtml


def test_artifact_models_validate_pipeline_outputs(tmp_path):
    original_base_dir = settings.base_dir
    original_environment = settings.environment
    original_debug_errors = settings.debug_errors
    settings.base_dir = tmp_path / "data"
    settings.environment = "test"
    settings.debug_errors = False
    settings.ensure_dirs()

    try:
        sample = make_sample_mhtml(tmp_path / "typed-sample.mhtml")
        result = ingest_file(str(sample))
        doc_dir = settings.base_dir / result["doc_id"]

        execution_plan = json.loads((doc_dir / "system" / "execution_plan.json").read_text())
        reconciliation = json.loads((doc_dir / "validation" / "reconciliation.json").read_text())
        embedding_status = json.loads((doc_dir / "system" / "embedding_status.json").read_text())
        system_spec = json.loads((doc_dir / "system_spec.json").read_text())

        assert ExecutionPlanModel.model_validate(execution_plan).status in {"ok", "invalid"}
        assert ReconciliationModel.model_validate(reconciliation).status in {"ok", "needs_review"}
        assert EmbeddingStatusModel.model_validate(embedding_status).actual_backend in {"none", "deterministic", "sentence_transformers"}
        assert SystemSpecModel.model_validate(system_spec).meta.doc_id == result["doc_id"]
    finally:
        settings.base_dir = original_base_dir
        settings.environment = original_environment
        settings.debug_errors = original_debug_errors
