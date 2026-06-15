import logging
import sys
import pytest
from src.utils.logger import setup_logger

def test_setup_logger_properties():
    logger = setup_logger()
    assert logger.name == "InstaSync"
    assert logger.level == logging.INFO

    # Check for StreamHandler pointing to stdout
    handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout]
    assert len(handlers) >= 1

def test_setup_logger_idempotency():
    logger = logging.getLogger("InstaSync")
    # Clear handlers first to have a clean state if possible,
    # but since it's already imported and setup_logger was called at module level,
    # there should be at least one.

    initial_handler_count = len(logger.handlers)
    assert initial_handler_count >= 1, "Logger should have at least one handler from module import"

    # Call it again
    setup_logger()

    # This is expected to FAIL before the fix
    assert len(logger.handlers) == initial_handler_count, f"Expected {initial_handler_count} handlers, but got {len(logger.handlers)}"
