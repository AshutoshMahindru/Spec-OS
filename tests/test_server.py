"""Tests for the FastAPI server surface."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import spec_os.server as server_module
from spec_os.config import settings
from spec_os.errors import build_error_payload
from spec_os.orchestration.pipeline import ingest_multiple_files
from spec_os.orchestration.sample import make_sample_mhtml


@pytest.fixture(autouse=True)
def use_tmp_data_dir(tmp_path):
    original_base_dir = settings.base_dir
    original_environment = settings.environment
    original_debug_errors = settings.debug_errors
    original_max_upload_size = settings.max_upload_size_bytes
    settings.base_dir = tmp_path / "data"
    settings.environment = "production"
    settings.debug_errors = False
    settings.max_upload_size_bytes = 5 * 1024 * 1024
    settings.ensure_dirs()
    yield
    settings.base_dir = original_base_dir
    settings.environment = original_environment
    settings.debug_errors = original_debug_errors
    settings.max_upload_size_bytes = original_max_upload_size


@pytest.fixture
def client():
    with TestClient(server_module.app) as test_client:
        yield test_client


@pytest.fixture
def sample_upload(tmp_path):
    path = make_sample_mhtml(tmp_path / "sample.mhtml")
    return path.name, path.read_bytes()


class TestIngestEndpoint:
    def test_rejects_invalid_upload_extension(self, client):
        response = client.post("/api/ingest", files={"file": ("bad.txt", b"hello", "text/plain")})
        payload = response.json()

        assert response.status_code == 400
        assert payload["error_code"] == "INVALID_UPLOAD_TYPE"

    def test_cleans_up_temp_upload_after_success(self, client, sample_upload):
        filename, content = sample_upload
        response = client.post("/api/ingest", files={"file": (filename, content, "multipart/related")})

        assert response.status_code == 200
        assert list(settings.base_dir.glob("*.mhtml")) == []

    def test_returns_stable_error_envelope_on_ingestion_failure(self, client, sample_upload, monkeypatch):
        filename, content = sample_upload

        monkeypatch.setattr(
            server_module,
            "ingest_file",
            lambda _: build_error_payload(
                doc_id="doc-123",
                error_code="INGESTION_FAILED",
                message="Failed to ingest file",
            ),
        )

        response = client.post("/api/ingest", files={"file": (filename, content, "multipart/related")})
        payload = response.json()

        assert response.status_code == 500
        assert payload["error_code"] == "INGESTION_FAILED"
        assert "trace" not in payload


class TestDocumentListing:
    def test_merged_docs_show_up_in_api_listing(self, client, tmp_path):
        first = make_sample_mhtml(tmp_path / "first.mhtml")
        second = make_sample_mhtml(tmp_path / "second.mhtml")

        merged = ingest_multiple_files([str(first), str(second)])

        response = client.get("/api/docs")
        docs = response.json()
        doc_ids = {doc["doc_id"] for doc in docs}

        assert response.status_code == 200
        assert merged["merged_id"] in doc_ids

        summary = client.get(f"/api/docs/{merged['merged_id']}/summary").json()
        assert summary["doc_type"] == "MERGED"

    def test_openapi_exposes_typed_ingest_and_summary_models(self, client):
        response = client.get("/openapi.json")
        payload = response.json()

        assert response.status_code == 200
        paths = payload["paths"]
        ingest_schema = paths["/api/ingest"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        summary_schema = paths["/api/docs/{doc_id}/summary"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

        assert ingest_schema["$ref"].endswith("/IngestSuccessResponse")
        assert summary_schema["$ref"].endswith("/DocumentSummaryResponse")
