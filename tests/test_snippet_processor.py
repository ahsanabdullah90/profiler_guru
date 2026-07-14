"""Tests for the assessment snippet processor."""

from src.assessment.snippet_processor import (
    blocks_to_markdown,
    compress_consecutive_reactions,
    deduplicate,
    evenly_sample,
    filter_empty_bodies,
    filter_low_value_bodies,
    split_blocks,
)

_SAMPLE = (
    "### [2026-03-12 11:10:52] labu_buu05\n"
    "Hello!\n"
    "<!-- chunk_id: a1b2 -->\n"
    "---\n"
    "### [2026-03-12 11:11:00] labu_buu05\n"
    "Reacted 😂 to your message\n"
    "---\n"
    "### [2026-03-12 11:12:00] labu_buu05\n"
    "Reacted 😂 to your message\n"
    "---\n"
    "### [2026-03-12 11:13:00] Ahsan Abdullah\n"
    "How are you?\n"
    "---\n"
    "### [2026-03-12 11:14:00] labu_buu05\n"
    "\n"
    "---\n"
    "### [2026-03-12 11:15:00] Ahsan Abdullah\n"
    "Reacted 😂 to your message\n"
)


class TestSplitBlocks:
    def test_splits_by_separator(self):
        blocks = split_blocks(_SAMPLE)
        assert len(blocks) == 6

    def test_parses_header(self):
        blocks = split_blocks(_SAMPLE)
        assert blocks[0]["timestamp"] == "2026-03-12 11:10:52"
        assert blocks[0]["sender"] == "labu_buu05"
        assert "Hello!" in blocks[0]["body"]

    def test_handles_empty_body(self):
        blocks = split_blocks(_SAMPLE)
        assert blocks[4]["body"] == ""

    def test_handles_non_header_block(self):
        raw = "Some raw text without header\n---\n### [t] s\nbody"
        blocks = split_blocks(raw)
        assert len(blocks) == 2
        assert blocks[0]["sender"] == ""
        assert "raw" in blocks[0]


class TestCompressReactions:
    def test_merges_consecutive_identical(self):
        blocks = split_blocks(_SAMPLE)
        compressed = compress_consecutive_reactions(blocks)
        assert len(compressed) == 5  # 6 blocks → 5 (two reactions merged)
        # The second block should now have count 2
        assert compressed[1]["count"] == 2
        assert compressed[1]["body"] == "Reacted 😂 to your message"
        assert compressed[1]["sender"] == "labu_buu05"

    def test_does_not_merge_different_senders(self):
        blocks = split_blocks(_SAMPLE)
        compressed = compress_consecutive_reactions(blocks)
        # Blocks 2 and 5 (0-indexed) have same body "Reacted 😂" but different
        # senders (labu_buu05 vs Ahsan Abdullah) — should NOT merge
        assert compressed[1]["sender"] == "labu_buu05"
        assert compressed[4]["sender"] == "Ahsan Abdullah"

    def test_empty_input(self):
        assert compress_consecutive_reactions([]) == []


class TestFilterEmpty:
    def test_removes_empty_blocks(self):
        blocks = split_blocks(_SAMPLE)
        filtered = filter_empty_bodies(blocks)
        assert len(filtered) == 5  # 6 blocks → 5 (empty body removed)

    def test_chunk_id_only_removed(self):
        raw = "### [t] s\n<!-- chunk_id: x -->\n"
        block = split_blocks(raw)
        assert filter_empty_bodies(block) == []


class TestFilterLowValue:
    def test_removes_reactions(self):
        blocks = split_blocks(_SAMPLE)
        cleaned = filter_low_value_bodies(blocks)
        # Removes Reacted, Liked, attachment, emoji-only blocks
        # labu_buu05's "Reacted 😂" and Ahsan's "Reacted 😂" are removed
        assert len(cleaned) == 2  # "Hello!" and "How are you?"

    def test_preserves_text(self):
        blocks = split_blocks(_SAMPLE)
        cleaned = filter_low_value_bodies(blocks)
        assert any("Hello!" in b["body"] for b in cleaned)
        assert any("How are you?" in b["body"] for b in cleaned)


class TestDeduplicate:
    def test_identical_from_same_sender_dropped(self):
        raw = (
            "### [t1] s\nHello\n---\n### [t2] s\nHello\n---\n### [t3] s\nOther"
        )
        blocks = split_blocks(raw)
        deduped = deduplicate(blocks)
        assert len(deduped) == 2  # second "Hello" dropped

    def test_identical_from_different_senders_kept(self):
        raw = "### [t1] A\nHi\n---\n### [t2] B\nHi"
        blocks = split_blocks(raw)
        deduped = deduplicate(blocks)
        assert len(deduped) == 2


class TestEvenlySample:
    def test_returns_all_when_under_max(self):
        blocks = [{"body": str(i)} for i in range(5)]
        assert len(evenly_sample(blocks, 10)) == 5

    def test_distributes_proportionally(self):
        blocks = [{"body": str(i)} for i in range(100)]
        sampled = evenly_sample(blocks, 10)
        assert len(sampled) == 10
        # Should include first and last
        assert sampled[0]["body"] == "0"
        assert sampled[-1]["body"] == "99"

    def test_not_just_head(self):
        blocks = [{"body": str(i)} for i in range(100)]
        sampled = evenly_sample(blocks, 10)
        indices = [int(b["body"]) for b in sampled]
        # At least one sample beyond the first quarter
        assert max(indices) > 25


class TestBlocksToMarkdown:
    def test_round_trip(self):
        blocks = split_blocks(_SAMPLE)
        md = blocks_to_markdown(blocks)
        assert "### [2026-03-12 11:10:52]" in md
        assert "Hello!" in md
        assert "---" in md

    def test_compressed_format(self):
        blocks = split_blocks(_SAMPLE)
        compressed = compress_consecutive_reactions(blocks)
        md = blocks_to_markdown(compressed)
        assert "[2×]" in md or "[2x]" in md
