"""HTML -> structured sections (headings + paragraphs)."""

from __future__ import annotations

import re
from typing import Any

from spec_os.helpers import normalize_text

try:
    from bs4 import BeautifulSoup  # type: ignore[import-untyped]

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False
    BeautifulSoup = None  # type: ignore[assignment,misc]


Section = dict[str, Any]


def clean_html(html: str) -> list[Section]:
    """Parse *html* into a list of ``{type, text, [level]}`` section dicts."""
    sections: list[Section] = []
    html = normalize_text(html)
    if not html:
        return sections

    if _HAS_BS4:
        return _clean_with_bs4(html)
    return _clean_naive(html)


def _clean_with_bs4(html: str) -> list[Section]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    sections: list[Section] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = normalize_text(tag.get_text(separator=" ", strip=True))
        if not text:
            continue
        if tag.name.startswith("h"):
            level = int(tag.name[1]) if tag.name[1:].isdigit() else 1
            sections.append({"type": "heading", "level": level, "text": text})
        else:
            sections.append({"type": "paragraph", "text": text})
    return sections


def _clean_naive(html: str) -> list[Section]:
    """Regex-based fallback when BeautifulSoup is unavailable."""
    stripped = re.sub(r"<[^>]+>", "\n", html)
    sections: list[Section] = []
    for line in stripped.splitlines():
        text = normalize_text(line.strip())
        if not text:
            continue
        if len(text) < 100 and (text.isupper() or re.match(r"^\d+\.", text)):
            sections.append({"type": "heading", "level": 2, "text": text})
        else:
            sections.append({"type": "paragraph", "text": text})
    return sections
