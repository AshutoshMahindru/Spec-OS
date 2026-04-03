"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def prd_structured():
    """Minimal PRD-like structured sections."""
    return [
        {"type": "heading", "level": 1, "text": "Product Requirements Document v3.0"},
        {"type": "paragraph", "text": "Functional Requirements"},
        {"type": "heading", "level": 2, "text": "Finance-First Philosophy"},
        {"type": "paragraph", "text": "Orders * AOV = Revenue"},
    ]


@pytest.fixture
def finance_structured():
    """Finance heading + formula paragraph."""
    return [
        {"type": "heading", "level": 2, "text": "Finance"},
        {"type": "paragraph", "text": "Orders * AOV = Revenue"},
    ]


@pytest.fixture
def architecture_structured():
    return [
        {"type": "heading", "level": 1, "text": "Layered Architecture"},
        {"type": "paragraph", "text": "Input Layer feeds Simulation Engine"},
        {"type": "paragraph", "text": "Simulation Engine outputs to Analytics Engine"},
    ]


@pytest.fixture
def data_dictionary_structured():
    return [
        {"type": "heading", "level": 2, "text": "17. Data Model Summary"},
        {"type": "paragraph", "text": "Planning Grain Key: company_id + scenario_id + assumption_set_id + planning_period_id"},
        {"type": "paragraph", "text": "Audit Fields: created_by, updated_by, created_at, updated_at"},
    ]


@pytest.fixture
def api_structured():
    return [
        {"type": "heading", "level": 2, "text": "API Design"},
        {"type": "paragraph", "text": "GET /planning/"},
    ]


@pytest.fixture
def corpus_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "corpus"


@pytest.fixture
def realistic_corpus(corpus_dir: Path) -> dict[str, Path]:
    return {
        "prd": corpus_dir / "prd_finance_planning.mhtml",
        "api": corpus_dir / "api_platform_contracts.mhtml",
        "architecture": corpus_dir / "architecture_engine_flow.mhtml",
        "data_dictionary": corpus_dir / "data_dictionary_planning_models.mhtml",
    }
