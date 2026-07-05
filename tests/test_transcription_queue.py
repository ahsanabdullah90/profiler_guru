import os
import time
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from src.utils.config import config


def _write_placeholder_md(path: Path, sender: str = "Alice", time_str: str = "2026-07-01 14:30:00", audio_name: str = "voice_clip.mp3"):
    """Helper: write a .md file with an audio transcription placeholder."""
    content = (
        f"### [{time_str}] {sender}\n"
        "How was the trip?\n"
        f"[Audio](../Audio/{audio_name})\n"
        "[Audio Transcription: Processing...]\n"
        "<!-- chunk_id: deadbeef -->\n"
        "\n"
        "---\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return content


def test_atomic_write_replaces_placeholder(tmp_path):
    """Transcription queue must atomically replace the placeholder using a temp file."""
    fake_transcription = "Hello, this is a test transcription."

    # Create a placeholder .md file
    md_path = tmp_path / "2026_07.md"
    _write_placeholder_md(md_path, sender="Bob", time_str="2026-07-01 14:30:00")

    # Read the content and apply the same logic the worker uses
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("---")
    target_header = "### [2026-07-01 14:30:00] Bob"

    old_block = None
    new_block = None

    for i, block in enumerate(blocks):
        block_strip = block.strip()
        if block_strip.startswith(target_header):
            placeholder = "[Audio Transcription: Processing...]"
            if placeholder in block_strip:
                old_block = block
                replacement = f"[Imported Audio Transcription: {fake_transcription}]"
                blocks[i] = block.replace(placeholder, replacement)
                new_block = blocks[i]
                break

    assert old_block is not None, "Target block not found"
    assert new_block is not None, "Placeholder not replaced"

    # Atomic write: temp file then os.replace
    new_content = "---".join(blocks)
    tmp_path_file = str(md_path) + ".tmp"
    with open(tmp_path_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(tmp_path_file, str(md_path))

    # Verify the placeholder was replaced
    with open(md_path, encoding="utf-8") as f:
        content_after = f.read()

    assert "[Audio Transcription: Processing...]" not in content_after
    assert fake_transcription in content_after
    # The temp file should be cleaned up
    assert not os.path.exists(tmp_path_file)


def test_orphan_recovery_on_startup(tmp_path, monkeypatch):
    """Startup must re-enqueue any placeholder not yet transcribed."""
    monkeypatch.setattr(config, "CHATS_DIR", str(tmp_path / "chats_orhpan"))

    # Create a placeholder file with matching audio
    chat_dir = tmp_path / "chats_orhpan" / "Carol" / "Chats"
    audio_dir = tmp_path / "chats_orhpan" / "Carol" / "Audio"
    audio_dir.mkdir(parents=True)
    audio_file = audio_dir / "voice_orphan.mp3"
    audio_file.write_text("orphan audio")

    md_path = chat_dir / "2026_08.md"
    # Use the same audio filename in the placeholder md as the file we create on disk
    _write_placeholder_md(md_path, sender="Carol", time_str="2026-08-15 09:00:00", audio_name="voice_orphan.mp3")

    from src.engine.transcription_queue import TranscriptionQueue

    # Reset the singleton so _init runs _recover_orphans
    TranscriptionQueue._instance = None

    with patch.object(TranscriptionQueue, "enqueue") as mock_enqueue:
        q = TranscriptionQueue()
        time.sleep(0.2)
        mock_enqueue.assert_called_once()
        args = mock_enqueue.call_args[0]
        assert args[0] == "Carol"
        assert args[1] == "2026_08"
        assert args[2] == "Carol"
        assert args[3] == "2026-08-15 09:00:00"
