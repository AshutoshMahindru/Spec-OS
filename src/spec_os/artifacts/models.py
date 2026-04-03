"""Typed artifact payload models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CitationModel(BaseModel):
    section_index: int | None = None
    source_tag: str | None = None
    section_title: str | None = None
    text: str


class TraceabilityRowModel(BaseModel):
    source_section: str
    artifact_type: str
    artifact_name: str | None = None
    status: str
    citations: list[CitationModel] = Field(default_factory=list)


class ReconciliationIssueModel(BaseModel):
    type: str
    variable: str | None = None
    metric: str | None = None
    endpoint: str | None = None
    model: str | None = None
    api: dict[str, Any] | None = None


class ReconciliationModel(BaseModel):
    issues: list[ReconciliationIssueModel] = Field(default_factory=list)
    status: Literal["ok", "needs_review"]


class ExecutionStepModel(BaseModel):
    step: int
    compute: str
    inputs: list[str] = Field(default_factory=list)


class ExecutionPlanIssueModel(BaseModel):
    type: str
    metric: str | None = None
    dependency: str | None = None
    metrics: list[str] | None = None


class ExecutionPlanModel(BaseModel):
    execution_steps: list[ExecutionStepModel] = Field(default_factory=list)
    issues: list[ExecutionPlanIssueModel] = Field(default_factory=list)
    status: Literal["ok", "invalid"]


class EmbeddingStatusModel(BaseModel):
    enabled: bool
    requested_backend: str
    actual_backend: str
    available: bool
    stored: bool
    reason: str


class SystemSpecMetaModel(BaseModel):
    doc_id: str
    doc_type: str
    spec_score: float | int | None = None
    ready_for_codegen: bool
    embedding_backend: str


class SystemSpecModel(BaseModel):
    meta: SystemSpecMetaModel
    sources: list[dict[str, Any]] = Field(default_factory=list)
    canonical: dict[str, Any]
    data_model: dict[str, Any]
    application: dict[str, Any]
    computation: dict[str, Any]
    runtime: dict[str, Any]
    validation: dict[str, Any]
