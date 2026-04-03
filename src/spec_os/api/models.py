"""Typed API response models for stable server endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: Literal["error"]
    error_code: str
    message: str
    doc_id: str | None = None
    details: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None


class IngestSuccessResponse(BaseModel):
    doc_id: str
    spec_dir: str
    chunks: int
    doc_type: str
    graph_nodes: int
    graph_edges: int
    schema_models: int
    schema_apis: int
    traceability_rows: int
    metrics: int
    apis: int
    variables: int
    reconciliation_issues: int
    spec_score: float | int | None
    ready_for_codegen: bool
    status: Literal["processed"]
    embedding_backend: str = "none"


class DocumentListItem(BaseModel):
    doc_id: str
    doc_type: str
    spec_score: float | int | None = None
    ready_for_codegen: bool | None = None


class DeleteResponse(BaseModel):
    status: Literal["deleted"]
    doc_id: str


class DocumentSummaryResponse(BaseModel):
    doc_id: str
    doc_type: str
    spec_score: float | int | None = None
    ready_for_codegen: bool = False
    graph_nodes: int
    graph_edges: int
    schema_models: int
    variables: int
    metrics: int
    apis: int


class HealthResponse(BaseModel):
    status: Literal["ok"]
