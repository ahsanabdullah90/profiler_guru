"""Unit tests for rag_engine helper functions:
- chunk_text()
- extract_date_range()
- chunk_block_respecting_boundaries()
"""
import pytest
from src.engine.rag_engine import (
    chunk_text,
    extract_date_range,
    chunk_block_respecting_boundaries,
)


# ── chunk_text ────────────────────────────────────────────────────────────

class TestChunkText:
    def test_short_text_not_chunked(self):
        """Text shorter than max_chars should return as a single chunk."""
        result = chunk_text("Hello world", max_chars=2000)
        assert result == ["Hello world"]

    def test_exact_max_chars(self):
        """Text at exactly max_chars should return as a single chunk."""
        text = "a" * 2000
        result = chunk_text(text, max_chars=2000)
        assert len(result) == 1
        assert result[0] == text

    def test_long_text_chunked(self):
        """Text exceeding max_chars should be split into multiple chunks."""
        text = "word " * 1000  # ~5000 chars
        result = chunk_text(text, max_chars=1000, overlap=100)
        assert len(result) > 1
        # All chunks combined should cover the original text
        combined = " ".join(result)
        assert "word" in combined

    def test_empty_text(self):
        """Empty text should return a single empty chunk."""
        result = chunk_text("", max_chars=2000)
        assert result == [""]

    def test_overlap_prevents_data_loss(self):
        """Chunks should overlap to preserve context at boundaries."""
        text = "A" * 500 + "\n" + "B" * 500 + "\n" + "C" * 500
        result = chunk_text(text, max_chars=600, overlap=200)
        assert len(result) >= 2
        # Both sections should appear in the output
        full = "\n".join(result)
        assert "A" * 100 in full
        assert "C" * 100 in full


# ── extract_date_range ────────────────────────────────────────────────────

class TestExtractDateRange:
    def test_single_timestamp(self):
        chunk = "### [2023-11-14 10:00:00] Alice\nHello!"
        result = extract_date_range(chunk)
        assert result == "2023-11-14 10:00:00"

    def test_multiple_timestamps(self):
        chunk = "### [2023-11-14 10:00:00] Alice\nHello!\n### [2023-11-15 12:00:00] Bob\nHi!"
        result = extract_date_range(chunk)
        assert "2023-11-14" in result
        assert "2023-11-15" in result
        assert " to " in result

    def test_no_timestamps(self):
        chunk = "Just some plain text without timestamps"
        result = extract_date_range(chunk)
        assert result == "unknown"


# ── chunk_block_respecting_boundaries ─────────────────────────────────────

class TestChunkBlockRespectingBoundaries:
    def test_short_block_single_chunk(self):
        block = "### [2023-11-14] Alice\nHello world"
        result = chunk_block_respecting_boundaries(block, max_chars=2000)
        assert len(result) == 1
        assert "Hello world" in result[0]

    def test_chunk_id_preserved(self):
        block = "### [2023-11-14] Alice\nHello\n<!-- chunk_id: abc12345 -->"
        result = chunk_block_respecting_boundaries(block, max_chars=2000)
        assert len(result) == 1
        assert "chunk_id: abc12345" in result[0]

    def test_long_block_split_preserves_chunk_id(self):
        """Long blocks should be split but preserve chunk_id in each sub-chunk."""
        long_text = "word " * 1000  # ~5000 chars
        block = f"### [2023-11-14] Alice\n{long_text}\n<!-- chunk_id: deadbeef -->"
        result = chunk_block_respecting_boundaries(block, max_chars=1000, overlap=200)
        assert len(result) > 1
        # Every sub-chunk should contain the chunk_id
        for chunk in result:
            assert "chunk_id: deadbeef" in chunk

    def test_no_chunk_id_still_works(self):
        """Blocks without chunk_id should work fine."""
        long_text = "word " * 1000
        block = f"### [2023-11-14] Alice\n{long_text}"
        result = chunk_block_respecting_boundaries(block, max_chars=1000, overlap=200)
        assert len(result) > 1
        # No chunk_id in any sub-chunk
        for chunk in result:
            assert "chunk_id" not in chunk
