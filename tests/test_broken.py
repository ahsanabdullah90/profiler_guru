import pytest
import os
from unittest.mock import MagicMock, patch
from src.engine.data_importer import InstagramDataImporter

def test_import_non_existent_path(temp_storage):
    importer = InstagramDataImporter(temp_storage)
    # This should return False and log an error
    success = importer.import_from_json("/non/existent/path")
    assert success is False

def test_storage_manager_invalid_timestamp(temp_storage):
    # Testing that storage manager handles invalid timestamp gracefully by falling back to current time
    try:
        content, file_path, month_id = temp_storage.save_message("Alice", "Alice", "Hi", "not_a_number")
        assert os.path.exists(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        assert "Alice" in saved_content
        assert "Hi" in saved_content
    except Exception as e:
        pytest.fail(f"save_message crashed with invalid timestamp: {e}")
