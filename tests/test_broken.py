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
    # Testing how storage manager handles invalid timestamp
    # It currently assumes timestamp / 1000.0 works if it's int/float
    # We expect an exception, but it could be AttributeError or TypeError
    with pytest.raises((AttributeError, TypeError)):
        temp_storage.save_message("Alice", "Alice", "Hi", "not_a_number")
