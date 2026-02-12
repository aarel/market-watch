import logging
import importlib
from pathlib import Path

import logging_config as lc


def _restore_logger(root_logger, handlers, level):
    root_logger.handlers[:] = handlers
    root_logger.setLevel(level)


def test_setup_logging_without_file(tmp_path):
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    old_level = root_logger.level
    try:
        lc.setup_logging(log_level="WARNING", log_file=None)
        assert root_logger.level == logging.WARNING
        assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
        assert not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    finally:
        _restore_logger(root_logger, old_handlers, old_level)


def test_setup_logging_with_file(tmp_path):
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    old_level = root_logger.level
    try:
        log_file = tmp_path / "logs" / "app.log"
        lc.setup_logging(log_level="DEBUG", log_file=str(log_file))
        assert root_logger.level == logging.DEBUG
        assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
        assert any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
        assert log_file.exists()
    finally:
        _restore_logger(root_logger, old_handlers, old_level)


def test_get_logger_returns_logger():
    logger = lc.get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"
