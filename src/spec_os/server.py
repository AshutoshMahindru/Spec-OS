"""FastAPI application for Spec-OS."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from spec_os.api.models import (
    DeleteResponse,
    DocumentListItem,
    DocumentSummaryResponse,
    ErrorResponse,
    HealthResponse,
    IngestSuccessResponse,
)
from spec_os.artifacts import (
    delete_document_bundle,
    list_document_dirs,
    load_json_artifact,
    load_text_artifact,
)
from spec_os.artifacts import (
    doc_dir as artifact_doc_dir,
)
from spec_os.config import settings
from spec_os.errors import build_error_payload
from spec_os.orchestration.pipeline import ingest_file

UPLOAD_FILE = File(...)

app = FastAPI(
    title="Spec-OS",
    description="Contract-first MHTML ingestion service",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _doc_dir(doc_id: str) -> Path:
    d = artifact_doc_dir(settings.base_dir, doc_id)
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return d


def _json_error_response(
    *,
    status_code: int,
    doc_id: str | None,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            doc_id=doc_id,
            error_code=error_code,
            message=message,
            details=details,
        ),
    )


def _load_json(doc_id: str, artifact_name: str) -> Any:
    try:
        return load_json_artifact(settings.base_dir, doc_id, artifact_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_name}") from exc


def _load_text(doc_id: str, artifact_name: str) -> str:
    try:
        return load_text_artifact(settings.base_dir, doc_id, artifact_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_name}") from exc


def _validate_upload(file: UploadFile, content: bytes) -> JSONResponse | None:
    filename = file.filename or "upload.mhtml"
    extension = Path(filename).suffix.lower()
    if extension not in settings.normalized_upload_extensions:
        return _json_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            doc_id=None,
            error_code="INVALID_UPLOAD_TYPE",
            message="Unsupported upload type",
            details={"filename": filename, "allowed_extensions": list(settings.normalized_upload_extensions)},
        )

    if file.content_type and file.content_type not in settings.allowed_upload_content_types:
        return _json_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            doc_id=None,
            error_code="INVALID_UPLOAD_CONTENT_TYPE",
            message="Unsupported upload content type",
            details={"content_type": file.content_type},
        )

    if len(content) > settings.max_upload_size_bytes:
        return _json_error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            doc_id=None,
            error_code="UPLOAD_TOO_LARGE",
            message="Upload exceeds maximum size",
            details={"max_upload_size_bytes": settings.max_upload_size_bytes},
        )

    return None


# ── Ingestion ───────────────────────────────────────────────────────────────

@app.post(
    "/api/ingest",
    response_model=IngestSuccessResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def ingest_endpoint(file: UploadFile = UPLOAD_FILE):
    settings.ensure_dirs()
    content = await file.read()
    validation_error = _validate_upload(file, content)
    if validation_error is not None:
        return validation_error

    suffix = Path(file.filename or "upload.mhtml").suffix or ".mhtml"
    file_path = settings.base_dir / f"{uuid.uuid4()}{suffix}"
    try:
        file_path.write_bytes(content)
        result = ingest_file(str(file_path))
    finally:
        if file_path.exists():
            file_path.unlink()

    if result.get("status") == "error":
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=result)
    return JSONResponse(content=result)


# Keep legacy route working
@app.post(
    "/ingest",
    response_model=IngestSuccessResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def ingest_legacy(file: UploadFile = UPLOAD_FILE):
    return await ingest_endpoint(file)


# ── List all ingested docs ──────────────────────────────────────────────────

@app.get("/api/docs", response_model=list[DocumentListItem])
async def list_docs():
    settings.ensure_dirs()
    docs = []
    for d in list_document_dirs(settings.base_dir):
        spec = _load_json(d.name, "system_spec")
        meta = spec.get("meta", {})
        docs.append({
            "doc_id": meta.get("doc_id", d.name),
            "doc_type": meta.get("doc_type", "UNKNOWN"),
            "spec_score": meta.get("spec_score"),
            "ready_for_codegen": meta.get("ready_for_codegen"),
        })
    return docs


# ── Delete a document ──────────────────────────────────────────────────────

@app.delete("/api/docs/{doc_id}", response_model=DeleteResponse)
async def delete_doc(doc_id: str):
    _doc_dir(doc_id)
    delete_document_bundle(settings.base_dir, doc_id)
    return {"status": "deleted", "doc_id": doc_id}


# ── Document summary (lightweight meta for sidebar) ─────────────────────────

@app.get("/api/docs/{doc_id}/summary", response_model=DocumentSummaryResponse)
async def get_doc_summary(doc_id: str):
    _doc_dir(doc_id)
    spec = _load_json(doc_id, "system_spec")
    meta = spec.get("meta", {})
    # Gather counts from the actual artifacts
    graph = {}
    schema = {}
    vars_reg = {}
    comp = {}
    api_c = []
    for artifact_name, target in (
        ("graph", "graph"),
        ("schema", "schema"),
        ("variable_registry", "vars_reg"),
        ("computation_graph", "comp"),
        ("api_contracts", "api_c"),
    ):
        try:
            payload = _load_json(doc_id, artifact_name)
        except HTTPException:
            continue
        if target == "graph":
            graph = payload
        elif target == "schema":
            schema = payload
        elif target == "vars_reg":
            vars_reg = payload
        elif target == "comp":
            comp = payload
        else:
            api_c = payload
    return {
        "doc_id": meta.get("doc_id", doc_id),
        "doc_type": meta.get("doc_type", "UNKNOWN"),
        "spec_score": meta.get("spec_score", 0),
        "ready_for_codegen": meta.get("ready_for_codegen", False),
        "graph_nodes": len(graph.get("nodes", [])),
        "graph_edges": len(graph.get("edges", [])),
        "schema_models": len(schema.get("models", [])),
        "variables": len(vars_reg.get("variables", [])),
        "metrics": len(comp.get("metrics", [])),
        "apis": len(api_c) if isinstance(api_c, list) else 0,
    }


# ── Full system spec ────────────────────────────────────────────────────────

@app.get("/api/docs/{doc_id}/spec")
async def get_system_spec(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "system_spec")


# ── Individual artifacts ────────────────────────────────────────────────────

@app.get("/api/docs/{doc_id}/graph")
async def get_graph(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "graph")


@app.get("/api/docs/{doc_id}/structured")
async def get_structured(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "structured")


@app.get("/api/docs/{doc_id}/canonical")
async def get_canonical(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "canonical_model")


@app.get("/api/docs/{doc_id}/variables")
async def get_variables(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "variable_registry")


@app.get("/api/docs/{doc_id}/schema")
async def get_schema(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "schema")


@app.get("/api/docs/{doc_id}/canonical-schema")
async def get_canonical_schema(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "canonical_schema")


@app.get("/api/docs/{doc_id}/computation")
async def get_computation(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "computation_graph")


@app.get("/api/docs/{doc_id}/api-contracts")
async def get_api_contracts(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "api_contracts")


@app.get("/api/docs/{doc_id}/mermaid")
async def get_mermaid(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "mermaid")


@app.get("/api/docs/{doc_id}/roadmap")
async def get_roadmap(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "roadmap")


@app.get("/api/docs/{doc_id}/traceability")
async def get_traceability(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "traceability")


@app.get("/api/docs/{doc_id}/ddl")
async def get_ddl(doc_id: str):
    _doc_dir(doc_id)
    return PlainTextResponse(_load_text(doc_id, "ddl_sql"))


@app.get("/api/docs/{doc_id}/reconciliation")
async def get_reconciliation(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "reconciliation")


@app.get("/api/docs/{doc_id}/completeness")
async def get_completeness(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "completeness")


@app.get("/api/docs/{doc_id}/score")
async def get_score(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "spec_score")


@app.get("/api/docs/{doc_id}/execution-plan")
async def get_execution_plan(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "execution_plan")


@app.get("/api/docs/{doc_id}/variable-mapping")
async def get_variable_mapping(doc_id: str):
    _doc_dir(doc_id)
    return _load_json(doc_id, "variable_mapping")


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


# ── Static UI (mounted last so API routes take priority) ────────────────────

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="ui")
