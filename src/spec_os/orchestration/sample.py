"""Sample MHTML fixture for demo / smoke-testing."""

from __future__ import annotations

from pathlib import Path

_SAMPLE = (
    "From: <Saved by WebKit>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: multipart/related; boundary=----=_NextPart_000_0000;\n"
    "\n"
    "------=_NextPart_000_0000\n"
    "Content-Type: text/html; charset=us-ascii\n"
    "Content-Transfer-Encoding: 7bit\n\n"
    "<html><body>"
    "<h1>Product Requirements Document v1</h1>"
    "<h2>MVP Definition</h2><p>The MVP includes planning workflow support.</p>"
    "<h2>Finance-First Philosophy</h2><p>Orders * AOV = Revenue</p>"
    "<h2>Data Model Summary</h2><p>Planning Grain Key: company_id + scenario_id + planning_period_id</p>"
    "<h2>API Design</h2><p>Base Path: /api/v1/ | Auth: JWT Bearer Token</p>"
    "<p>/planning/ - Spines, Scenarios, Versions</p>"
    "</body></html>\n"
    "------=_NextPart_000_0000--\n"
)


def make_sample_mhtml(path: str | Path) -> Path:
    """Write a minimal MHTML sample and return the path."""
    path = Path(path)
    path.write_text(_SAMPLE, encoding="utf-8")
    return path
