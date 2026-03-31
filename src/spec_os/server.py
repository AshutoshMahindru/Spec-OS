"""FastAPI application for Spec-OS."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from spec_os.config import settings
from spec_os.orchestration.pipeline import ingest_file

app = FastAPI(
    title="Spec-OS",
    description="Contract-first MHTML ingestion service",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _doc_dir(doc_id: str) -> Path:
    d = settings.base_dir / doc_id
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return d


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path.name}")
    return json.loads(path.read_text())


# ── Ingestion ───────────────────────────────────────────────────────────────

@app.post("/api/ingest")
async def ingest_endpoint(file: UploadFile = File(...)):
    settings.ensure_dirs()
    file_path = settings.base_dir / f"{uuid.uuid4()}.mhtml"
    file_path.write_bytes(await file.read())
    result = ingest_file(str(file_path))
    return JSONResponse(content=result)


# Keep legacy route working
@app.post("/ingest")
async def ingest_legacy(file: UploadFile = File(...)):
    return await ingest_endpoint(file)


# ── List all ingested docs ──────────────────────────────────────────────────

@app.get("/api/docs")
async def list_docs():
    settings.ensure_dirs()
    docs = []
    for d in sorted(settings.base_dir.iterdir()):
        spec_file = d / "system_spec.json"
        if d.is_dir() and spec_file.exists():
            spec = json.loads(spec_file.read_text())
            meta = spec.get("meta", {})
            docs.append({
                "doc_id": meta.get("doc_id", d.name),
                "doc_type": meta.get("doc_type", "UNKNOWN"),
                "spec_score": meta.get("spec_score"),
                "ready_for_codegen": meta.get("ready_for_codegen"),
            })
    return docs


# ── Delete a document ──────────────────────────────────────────────────────

@app.delete("/api/docs/{doc_id}")
async def delete_doc(doc_id: str):
    doc = _doc_dir(doc_id)
    shutil.rmtree(doc)
    # Also remove the spec folder if it exists
    spec_folder = settings.base_dir / f"{doc_id}_spec"
    if spec_folder.exists():
        shutil.rmtree(spec_folder)
    return {"status": "deleted", "doc_id": doc_id}


# ── Document summary (lightweight meta for sidebar) ─────────────────────────

@app.get("/api/docs/{doc_id}/summary")
async def get_doc_summary(doc_id: str):
    d = _doc_dir(doc_id)
    spec = _load_json(d / "system_spec.json")
    meta = spec.get("meta", {})
    # Gather counts from the actual artifacts
    graph = {}
    schema = {}
    vars_reg = {}
    comp = {}
    api_c = []
    try:
        graph = json.loads((d / "layers" / "graph.json").read_text())
    except Exception:
        pass
    try:
        schema = json.loads((d / "domain" / "schema.json").read_text())
    except Exception:
        pass
    try:
        vars_reg = json.loads((d / "canonical" / "variable_registry.json").read_text())
    except Exception:
        pass
    try:
        comp = json.loads((d / "domain" / "computation_graph.json").read_text())
    except Exception:
        pass
    try:
        api_c = json.loads((d / "domain" / "api_contracts.json").read_text())
    except Exception:
        pass
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
    return _load_json(_doc_dir(doc_id) / "system_spec.json")


# ── Individual artifacts ────────────────────────────────────────────────────

@app.get("/api/docs/{doc_id}/graph")
async def get_graph(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "layers" / "graph.json")


@app.get("/api/docs/{doc_id}/structured")
async def get_structured(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "layers" / "structured.json")


@app.get("/api/docs/{doc_id}/canonical")
async def get_canonical(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "canonical" / "canonical_model.json")


@app.get("/api/docs/{doc_id}/variables")
async def get_variables(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "canonical" / "variable_registry.json")


@app.get("/api/docs/{doc_id}/schema")
async def get_schema(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "domain" / "schema.json")


@app.get("/api/docs/{doc_id}/canonical-schema")
async def get_canonical_schema(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "domain" / "canonical_schema.json")


@app.get("/api/docs/{doc_id}/computation")
async def get_computation(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "domain" / "computation_graph.json")


@app.get("/api/docs/{doc_id}/api-contracts")
async def get_api_contracts(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "domain" / "api_contracts.json")


@app.get("/api/docs/{doc_id}/mermaid")
async def get_mermaid(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "artifacts" / "mermaid.json")


@app.get("/api/docs/{doc_id}/roadmap")
async def get_roadmap(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "artifacts" / "roadmap.json")


@app.get("/api/docs/{doc_id}/traceability")
async def get_traceability(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "artifacts" / "traceability.json")


@app.get("/api/docs/{doc_id}/ddl")
async def get_ddl(doc_id: str):
    ddl_path = _doc_dir(doc_id) / "artifacts" / "ddl.sql"
    if not ddl_path.exists():
        raise HTTPException(status_code=404, detail="DDL not found")
    return PlainTextResponse(ddl_path.read_text())


@app.get("/api/docs/{doc_id}/reconciliation")
async def get_reconciliation(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "validation" / "reconciliation.json")


@app.get("/api/docs/{doc_id}/completeness")
async def get_completeness(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "validation" / "completeness.json")


@app.get("/api/docs/{doc_id}/score")
async def get_score(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "validation" / "spec_score.json")


@app.get("/api/docs/{doc_id}/execution-plan")
async def get_execution_plan(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "system" / "execution_plan.json")


@app.get("/api/docs/{doc_id}/variable-mapping")
async def get_variable_mapping(doc_id: str):
    return _load_json(_doc_dir(doc_id) / "system" / "variable_mapping.json")


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Static UI (mounted last so API routes take priority) ────────────────────

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="ui")
