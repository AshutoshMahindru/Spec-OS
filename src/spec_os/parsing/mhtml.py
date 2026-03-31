"""MHTML file parser -- extract the first HTML body from an MHTML archive."""

from __future__ import annotations

import logging
from email import policy
from email.parser import BytesParser
from pathlib import Path

from spec_os.helpers import normalize_text

logger = logging.getLogger(__name__)


def parse_mhtml(file_path: str | Path) -> str:
    """Return the HTML (or raw text) content of *file_path*.

    Strategy:
    1. Parse as MIME with ``BytesParser`` and return the first ``text/html`` part.
    2. Fall back to reading the file as plain UTF-8.
    """
    file_path = Path(file_path)

    try:
        with file_path.open("rb") as fh:
            msg = BytesParser(policy=policy.default).parse(fh)

        for part in msg.walk():
            if part.get_content_type() == "text/html":
                content = part.get_content()
                return normalize_text(str(content) if not isinstance(content, str) else content)
    except Exception:
        logger.debug("MIME parsing failed for %s, falling back to raw read", file_path)

    return normalize_text(file_path.read_text(encoding="utf-8", errors="ignore"))
