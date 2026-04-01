"""Shared error payload helpers for CLI and API surfaces."""

from __future__ import annotations

from typing import Any


def build_error_payload(
    *,
    doc_id: str | None,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable error envelope."""
    payload: dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "doc_id": doc_id,
    }

    if details:
        payload["details"] = details
    if debug:
        payload["debug"] = debug

    return payload
