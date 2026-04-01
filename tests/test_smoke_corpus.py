"""Smoke tests for a more realistic MHTML corpus."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import spec_os.server as server_module
from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_file


@pytest.fixture(autouse=True)
def use_tmp_data_dir(tmp_path):
    original_base_dir = settings.base_dir
    original_environment = settings.environment
    original_debug_errors = settings.debug_errors
    original_enable_embeddings = settings.enable_embeddings
    settings.base_dir = tmp_path / "data"
    settings.environment = "test"
    settings.debug_errors = False
    settings.enable_embeddings = False
    settings.ensure_dirs()
    yield
    settings.base_dir = original_base_dir
    settings.environment = original_environment
    settings.debug_errors = original_debug_errors
    settings.enable_embeddings = original_enable_embeddings


@pytest.mark.parametrize(
    ("corpus_key", "expected_doc_type"),
    [
        ("prd", "PRD"),
        ("api", "API_SPEC"),
        ("architecture", "ARCHITECTURE"),
        ("data_dictionary", "DATA_DICTIONARY"),
    ],
)
def test_pipeline_smoke_corpus(realistic_corpus, corpus_key, expected_doc_type):
    path = realistic_corpus[corpus_key]

    result = ingest_file(str(path))

    assert result["status"] == "processed"
    assert result["doc_type"] == expected_doc_type

    doc_dir = settings.base_dir / result["doc_id"]
    spec = json.loads((doc_dir / "system_spec.json").read_text())
    assert spec["meta"]["doc_type"] == expected_doc_type
    assert (doc_dir / "layers" / "graph.json").exists()
    assert (doc_dir / "validation" / "reconciliation.json").exists()


def test_cli_smoke_corpus(realistic_corpus, tmp_path):
    data_dir = tmp_path / "cli-data"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "spec_os.cli",
            "--file",
            str(realistic_corpus["prd"]),
            "--data-dir",
            str(data_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["status"] == "processed"
    assert payload["doc_type"] == "PRD"
    assert (Path(payload["spec_dir"]) / "canonical_schema.json").exists()


def test_api_smoke_corpus(realistic_corpus):
    with TestClient(server_module.app) as client:
        corpus_file = realistic_corpus["api"]
        response = client.post(
            "/api/ingest",
            files={
                "file": (
                    corpus_file.name,
                    corpus_file.read_bytes(),
                    "multipart/related",
                )
            },
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "processed"
    assert payload["doc_type"] == "API_SPEC"
