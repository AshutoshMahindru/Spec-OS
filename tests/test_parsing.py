"""Tests for parsing module."""

from __future__ import annotations

from spec_os.parsing.chunker import chunk_text
from spec_os.parsing.html_cleaner import clean_html


class TestCleanHtml:
    def test_extracts_headings_and_paragraphs(self):
        html = "<h1>Title</h1><p>Body text</p>"
        sections = clean_html(html)
        assert len(sections) == 2
        assert sections[0]["type"] == "heading"
        assert sections[0]["level"] == 1
        assert sections[1]["type"] == "paragraph"

    def test_strips_script_and_style(self):
        html = "<script>alert(1)</script><style>.x{}</style><p>Keep</p>"
        sections = clean_html(html)
        assert len(sections) == 1
        assert sections[0]["text"] == "Keep"

    def test_empty_html_returns_empty(self):
        assert clean_html("") == []
        assert clean_html(None) == []

    def test_normalises_dashes(self):
        html = "<p>A\u2013B\u2014C</p>"
        sections = clean_html(html)
        assert sections[0]["text"] == "A-B-C"


class TestChunkText:
    def test_chunks_split_on_heading(self):
        sections = [
            {"type": "heading", "level": 1, "text": "H1"},
            {"type": "paragraph", "text": "Body A"},
            {"type": "heading", "level": 2, "text": "H2"},
            {"type": "paragraph", "text": "Body B"},
        ]
        chunks = chunk_text(sections, "d1")
        assert len(chunks) == 2
        assert chunks[0]["heading"] == "H1"
        assert chunks[1]["heading"] == "H2"

    def test_respects_max_len(self):
        sections = [
            {"type": "paragraph", "text": "A" * 300},
            {"type": "paragraph", "text": "B" * 300},
        ]
        chunks = chunk_text(sections, "d2", max_len=500)
        assert len(chunks) == 2
