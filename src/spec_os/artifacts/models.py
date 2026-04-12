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
    """Flexible issue model that accepts any reconciliation issue type.

    Core fields are optional to accommodate all issue types:
    * MISSING_STORAGE_MAPPING: variable
    * MISSING_VARIABLE_IN_REGISTRY: variable, metric
    * API_SCHEMA_MISMATCH: endpoint, model
    * INVALID_API: api
    * CONFLICTING_FORMULA: metric, definitions
    * CONFLICTING_VARIABLE_TYPE: variable, observed_types
    * CONFLICTING_FIELD_TYPE: model, field, existing, incoming
    * BROKEN_EDGE / TYPE_MISMATCH_EDGE: edge_type, from, to
    * POSSIBLE_ALIAS: variable_a, variable_b, similarity
    * DUPLICATE_API: endpoint, method
    * CYCLE_DETECTED: metrics (list)
    * SELF_DEPENDENCY / UNRESOLVED_DEPENDENCY / DUPLICATE_METRIC: metric
    """
    type: str
    # Variable/metric identifiers.
    variable: str | None = None
    metric: str | None = None
    endpoint: str | None = None
    model: str | None = None
    api: dict[str, Any] | None = None
    # Change A: formula conflict details.
    definitions: list[dict[str, Any]] | None = None
    # Change A: variable type conflict details.
    observed_types: list[dict[str, Any]] | None = None
    # Change E: field conflict details.
    field: str | None = None
    existing: dict[str, Any] | None = None
    incoming: dict[str, Any] | None = None
    # Change C: edge integrity details.
    edge_type: str | None = None
    reason: str | None = None
    expected_src_type: str | None = None
    actual_src_type: str | None = None
    expected_dst_type: str | None = None
    actual_dst_type: str | None = None
    # Alias fields from edge dicts (from/to are Python keywords, use Field).
    from_id: str | None = Field(None, alias="from")
    to_id: str | None = Field(None, alias="to")
    # Change B: fuzzy alias fields.
    variable_a: str | None = None
    variable_b: str | None = None
    similarity: float | None = None
    # Change E: duplicate API details.
    method: str | None = None
    # Computation validation: CYCLE_DETECTED.
    metrics: list[str] | None = None
    # Computation validation: UNRESOLVED_DEPENDENCY.
    dependency: str | None = None

    model_config = {"populate_by_name": True}


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
