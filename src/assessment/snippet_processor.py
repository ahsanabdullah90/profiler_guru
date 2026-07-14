"""Assessment-scale block parsing, filtering, compression, sampling, and deduplication.

This module is used exclusively by the assessment pipeline and PDF report
generator.  It deliberately does NOT replace ``parse_message_blocks`` in
``src/utils/markdown.py`` — that function is shared infrastructure used by
the importer, contact merge, transcription, metrics backfill, ChromaDB
indexing, and other components that depend on stable block boundaries.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_BLOCK_SEP = re.compile(r"\n---\n")
_CHUNK_ID_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADER_RE = re.compile(r"^### \[(.+?)\] (.+)$")

_LOW_VALUE_BODIES: list[re.Pattern] = [
    re.compile(r"^Reacted .+ to your message\s*$"),
    re.compile(r"^Liked a message\s*$"),
    re.compile(r"^sent an attachment\.\s*$"),
    re.compile(r"^[\U0001F000-\U0001FFFF\s]+$"),
]


# ── Data container ──────────────────────────────────────────────────────


def _make_block(
    text: str,
    header: str = "",
    timestamp: str = "",
    sender: str = "",
    body: str = "",
) -> dict[str, Any]:
    return {
        "raw": text,
        "header": header,
        "timestamp": timestamp,
        "sender": sender,
        "body": body,
        "count": 1,
    }


# ── 1. Split ─────────────────────────────────────────────────────────────


def split_blocks(content: str) -> list[dict[str, Any]]:
    """Split markdown content on ``\\n---\\n`` boundaries.

    Returns a list of structured block dicts with *header*, *timestamp*,
    *sender*, and *body* fields.
    """
    blocks: list[dict[str, Any]] = []
    for raw in _BLOCK_SEP.split(content):
        raw = raw.strip()
        if not raw:
            continue
        lines = raw.split("\n")
        header_line = lines[0].strip()
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        m = _HEADER_RE.match(header_line)
        if m:
            blocks.append(
                _make_block(
                    text=raw,
                    header=header_line,
                    timestamp=m.group(1),
                    sender=m.group(2),
                    body=body,
                )
            )
        else:
            blocks.append(_make_block(text=raw, body=raw))
    return blocks


# ── 2. Compress consecutive reactions ────────────────────────────────────


def compress_consecutive_reactions(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge consecutive blocks from the *same sender* with the *same body*.

    The first occurrence's header and timestamp are preserved; a *count*
    field tracks how many were merged.  The body is prefixed with
    ``[N×] `` when *count* > 1.
    """
    if not blocks:
        return []

    result: list[dict[str, Any]] = []
    for block in blocks:
        if (
            result
            and result[-1]["sender"] == block["sender"]
            and result[-1]["body"] == block["body"]
        ):
            result[-1]["count"] += 1
            result[-1]["last_timestamp"] = block["timestamp"]
        else:
            result.append(dict(block))
    return result


# ── 3. Filter empty bodies ───────────────────────────────────────────────


def filter_empty_bodies(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove blocks whose *body* is empty or only chunk-id comments."""
    out: list[dict[str, Any]] = []
    for block in blocks:
        cleaned = _CHUNK_ID_RE.sub("", block["body"]).strip()
        if not cleaned:
            continue
        out.append(block)
    return out


# ── 4. Filter low-value bodies ───────────────────────────────────────────


def filter_low_value_bodies(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove blocks whose *body* matches known low-value patterns.

    This does **not** compress — call ``compress_consecutive_reactions``
    first to preserve the signal.
    """
    out: list[dict[str, Any]] = []
    for block in blocks:
        cleaned = _CHUNK_ID_RE.sub("", block["body"]).strip()
        if not cleaned:
            continue
        if any(p.match(cleaned) for p in _LOW_VALUE_BODIES):
            continue
        if len(cleaned) <= 3 and not cleaned.isalpha():
            continue
        out.append(block)
    return out


# ── 5. Deduplicate ───────────────────────────────────────────────────────


def deduplicate(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop blocks that share the same ``(sender, body)`` as an earlier block.

    Keeps the first chronological occurrence.  Used for snippet tables —
    not for the assessment prompt itself.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for block in blocks:
        key = (block["sender"], block["body"])
        if key not in seen:
            seen.add(key)
            out.append(block)
    return out


# ── 6. Even sampling ────────────────────────────────────────────────────


def evenly_sample(
    blocks: list[dict[str, Any]],
    max_count: int,
) -> list[dict[str, Any]]:
    """Select *max_count* blocks distributed proportionally over the list.

    Always includes the first and last block when possible.
    """
    if len(blocks) <= max_count or max_count < 2:
        return blocks
    step = (len(blocks) - 1) / (max_count - 1)
    result: list[dict[str, Any]] = []
    for i in range(max_count):
        idx = round(i * step)
        idx = min(idx, len(blocks) - 1)
        result.append(blocks[idx])
    return result


# ── 7. Reconstruct markdown ─────────────────────────────────────────────


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Reconstruct the ``\\n---\\n`` delimited markdown from a list of blocks.

    Compressed blocks (``count > 1``) are expanded inline:
    ::
        ### [first_ts] sender
        [3×] compressed body

    Blocks without a ``### [...`` header are emitted as raw text.
    """
    parts: list[str] = []
    for b in blocks:
        header = b.get("header", "")
        body = b.get("body", "")
        if b.get("count", 1) > 1 and body:
            body = f"[{b['count']}×] {body}"
        if header:
            parts.append(f"{header}\n{body}" if body else header)
        else:
            parts.append(b.get("raw", "") if body else body)
    return "\n---\n".join(parts)
